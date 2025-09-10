import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.protocol.printer import PrinterSession, PrinterJob
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import (
    SCS_DATA,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    PRINT_EOJ,
)


class TestPrinterJob:
    def test_init_default(self):
        """Test default initialization."""
        job = PrinterJob()
        assert len(job.job_id) > 0  # Should have auto-generated ID
        assert job.status == "active"
        assert len(job.data) == 0
        assert job.start_time is not None
        assert job.end_time is None

    def test_init_with_id(self):
        """Test initialization with custom ID."""
        job = PrinterJob("test_job")
        assert job.job_id == "test_job"
        assert job.status == "active"

    def test_add_data(self):
        """Test adding data to job."""
        job = PrinterJob("test")
        data1 = b"Hello"
        data2 = b" World"

        job.add_data(data1)
        assert len(job.data) == 5
        assert bytes(job.data) == b"Hello"

        job.add_data(data2)
        assert len(job.data) == 11
        assert bytes(job.data) == b"Hello World"

    def test_complete_job(self):
        """Test completing a job."""
        job = PrinterJob("test")
        job.add_data(b"Test data")

        job.complete_job()
        assert job.status == "completed"
        assert job.end_time is not None

    def test_set_error(self):
        """Test setting job error."""
        job = PrinterJob("test")
        job.add_data(b"Test data")

        job.set_error("Test error")
        assert job.status == "error"
        assert job.end_time is not None

    def test_get_duration(self):
        """Test getting job duration."""
        job = PrinterJob("test")
        duration1 = job.get_duration()
        assert duration1 >= 0

        # Complete job and check duration
        job.complete_job()
        duration2 = job.get_duration()
        assert duration2 >= 0

    def test_get_page_count(self):
        """Test getting page count."""
        job = PrinterJob("test")

        # Single page
        job.add_data(b"Single page content")
        assert job.get_page_count() == 1

        # Multiple pages with form feeds
        job.add_data(b"Page 1\x0cPage 2\x0cPage 3")
        assert job.get_page_count() == 3

    def test_get_data_size(self):
        """Test getting data size."""
        job = PrinterJob("test")
        assert job.get_data_size() == 0

        job.add_data(b"Test data")
        assert job.get_data_size() == 9

    def test_repr(self):
        """Test string representation."""
        job = PrinterJob("test")
        repr_str = repr(job)
        assert "PrinterJob" in repr_str
        assert "test" in repr_str


class TestPrinterSession:
    def test_init(self):
        """Test initialization."""
        session = PrinterSession()
        assert session.is_active is False
        assert session.current_job is None
        assert len(session.completed_jobs) == 0
        assert session.sequence_number == 0

    def test_activate_deactivate(self):
        """Test activation and deactivation."""
        session = PrinterSession()

        # Activate
        session.activate()
        assert session.is_active is True

        # Deactivate
        session.deactivate()
        assert session.is_active is False

    def test_start_new_job(self):
        """Test starting a new job."""
        session = PrinterSession()
        session.activate()

        job = session.start_new_job("test_job")
        assert session.current_job is job
        assert job.job_id == "test_job"
        assert job.status == "active"

    def test_start_new_job_without_activation(self):
        """Test starting a job without activation."""
        session = PrinterSession()

        with pytest.raises(Exception):  # ProtocolError
            session.start_new_job("test_job")

    def test_add_scs_data(self):
        """Test adding SCS data."""
        session = PrinterSession()
        session.activate()

        data = b"Test SCS data"
        session.add_scs_data(data)

        # Should have started a new job automatically
        assert session.current_job is not None
        assert len(session.current_job.data) == len(data)

    def test_handle_print_eoj(self):
        """Test handling PRINT-EOJ."""
        session = PrinterSession()
        session.activate()

        # Start a job
        job = session.start_new_job("test")
        job.add_data(b"Test data")

        # Handle EOJ
        session.handle_print_eoj()

        # Job should be completed and moved to completed jobs
        assert session.current_job is None
        assert len(session.completed_jobs) == 1
        assert session.completed_jobs[0] is job
        assert job.status == "completed"

    def test_handle_print_eoj_without_active_job(self):
        """Test handling PRINT-EOJ without active job."""
        session = PrinterSession()
        session.activate()

        # Should not raise an error
        session.handle_print_eoj()
        assert session.current_job is None
        assert len(session.completed_jobs) == 0

    def test_get_current_job(self):
        """Test getting current job."""
        session = PrinterSession()
        session.activate()

        assert session.get_current_job() is None

        job = session.start_new_job("test")
        assert session.get_current_job() is job

    def test_get_completed_jobs(self):
        """Test getting completed jobs."""
        session = PrinterSession()
        session.activate()

        assert len(session.get_completed_jobs()) == 0

        # Complete a job
        job = session.start_new_job("test1")
        job.add_data(b"Data 1")
        session.handle_print_eoj()

        completed = session.get_completed_jobs()
        assert len(completed) == 1
        assert completed[0].job_id == "test1"

    def test_get_job_statistics(self):
        """Test getting job statistics."""
        session = PrinterSession()
        session.activate()

        # Empty stats
        stats = session.get_job_statistics()
        assert stats["active_jobs"] == 0
        assert stats["completed_jobs"] == 0
        assert stats["total_pages"] == 0
        assert stats["total_bytes"] == 0

        # Add some jobs
        job1 = session.start_new_job("test1")
        job1.add_data(b"Page 1\x0cPage 2")
        session.handle_print_eoj()

        job2 = session.start_new_job("test2")
        job2.add_data(b"Single page")
        session.handle_print_eoj()

        stats = session.get_job_statistics()
        assert stats["active_jobs"] == 0
        assert stats["completed_jobs"] == 2
        assert stats["total_pages"] == 3  # 2 pages + 1 page
        assert stats["total_bytes"] == 24  # 13 + 11 bytes
        assert stats["average_pages_per_job"] == 1.5
        assert stats["average_bytes_per_job"] == 12.0

    def test_clear_completed_jobs(self):
        """Test clearing completed jobs."""
        session = PrinterSession()
        session.activate()

        # Add some completed jobs
        job1 = session.start_new_job("test1")
        job1.add_data(b"Data 1")
        session.handle_print_eoj()

        job2 = session.start_new_job("test2")
        job2.add_data(b"Data 2")
        session.handle_print_eoj()

        assert len(session.completed_jobs) == 2

        session.clear_completed_jobs()
        assert len(session.completed_jobs) == 0

    def test_handle_scs_control_code(self):
        """Test handling SCS control codes."""
        session = PrinterSession()
        session.activate()

        # Start a job
        job = session.start_new_job("test")
        job.add_data(b"Test data")

        # Handle PRINT_EOJ (0x08)
        session.handle_scs_control_code(PRINT_EOJ)  # PRINT_EOJ

        # Job should be completed
        assert session.current_job is None
        assert job.status == "completed"

    def test_handle_unknown_scs_control_code(self):
        """Test handling unknown SCS control codes."""
        session = PrinterSession()
        session.activate()

        # Should not raise error for unknown codes
        session.handle_scs_control_code(0xFF)

    def test_process_tn3270e_message_scs_data(self):
        """Test processing TN3270E SCS data message."""
        session = PrinterSession()
        session.activate()

        header = TN3270EHeader(data_type=TN3270E_SCS_CTL_CODES)
        data = b"Test SCS data"

        session.process_tn3270e_message(header, data)

        # Should have started a job and added data
        assert session.current_job is not None
        assert len(session.current_job.data) == len(data)

    def test_process_tn3270e_message_error_response(self):
        """Test processing TN3270E error response."""
        session = PrinterSession()
        session.activate()

        # Start a job
        job = session.start_new_job("test")

        header = TN3270EHeader(
            data_type=TN3270E_RESPONSES,  # RESPONSE
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=123,
        )
        data = b""

        session.process_tn3270e_message(header, data)

        # Job should have error status
        assert job.status == "error"

    def test_process_tn3270e_message_negative_response(self):
        """Test processing TN3270E negative response."""
        session = PrinterSession()
        session.activate()

        # Start a job
        job = session.start_new_job("test")
        job.add_data(b"Test data")

        # Use a different response flag value to distinguish from error responses
        header = TN3270EHeader(
            data_type=0x02,  # RESPONSE
            response_flag=0x03,  # Some non-error, non-positive response flag
            seq_number=123,
        )
        data = b""

        session.process_tn3270e_message(header, data)

        # Job should still be active but warning logged
        assert job.status == "active"

    def test_repr(self):
        """Test string representation."""
        session = PrinterSession()
        session.activate()

        repr_str = repr(session)
        assert "PrinterSession" in repr_str
        assert "active=True" in repr_str
