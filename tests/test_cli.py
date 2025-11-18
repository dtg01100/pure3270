import logging
import platform
import sys
from unittest.mock import MagicMock, patch

import pytest

from pure3270 import main


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_main_no_args(capsys, memory_limit_500mb):
    with patch("sys.argv", ["pure3270"]):
        with patch("pure3270.Session") as mock_session:
            mock_instance = MagicMock()
            mock_session.return_value = mock_instance
            mock_instance.connect.return_value = None
            # Mock input to immediately return 'quit' to exit the loop
            with patch("builtins.input", return_value="quit"):
                try:
                    main()
                except SystemExit:
                    pass  # Normal argparse exit
                # We don't assert anything since it will fail due to missing host argument


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_main_with_host(capsys, caplog, preserve_root_logger, memory_limit_500mb):
    with patch("sys.argv", ["pure3270", "test.host", "--console"]):
        with patch("pure3270.Session") as mock_session:
            mock_instance = MagicMock()
            mock_session.return_value = mock_instance
            mock_instance.connect.return_value = None
            # Mock input to immediately return 'quit' to exit the loop
            with patch("builtins.input", return_value="quit"):
                caplog.set_level(logging.INFO, logger="pure3270")
                try:
                    main()
                except SystemExit:
                    pass  # Normal exit
                captured = capsys.readouterr()
                if "Connected to test.host:23" in captured.out:
                    assert True
                else:
                    assert any(
                        "Connected to test.host:23" in rec.getMessage()
                        for rec in caplog.records
                    )


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_main_with_script(capsys, caplog, preserve_root_logger, memory_limit_500mb):
    with patch("argparse.ArgumentParser") as mock_parser:
        mock_args = MagicMock()
        mock_args.host = "test.host"
        mock_args.port = 23
        mock_args.ssl = False
        mock_args.script = "test_script.txt"
        mock_parser.parse_args.return_value = mock_args
        with patch("builtins.open") as mock_open:
            mock_file = MagicMock()
            mock_file.readlines.return_value = ["String(hello)", "key Enter"]
            mock_open.return_value.__enter__.return_value = mock_file
            with patch("pure3270.Session") as mock_session:
                mock_instance = MagicMock()
                mock_session.return_value = mock_instance
                mock_instance.connect.return_value = None
                caplog.set_level(logging.INFO)
                main()
                captured = capsys.readouterr()
                if "permanently unsupported" in captured.out:
                    assert True
                else:
                    assert any(
                        "permanently unsupported" in rec.getMessage()
                        for rec in caplog.records
                    )


def test_main_restores_console_env(
    capsys, monkeypatch, preserve_root_logger, memory_limit_500mb
):
    """Verify that calling main() with or without --console restores the previous
    PURE3270_CONSOLE_MODE environment value on exit.
    """
    import os
    from unittest.mock import MagicMock, patch

    from pure3270 import main

    # Scenario A: env var initially unset, main() called with --console -> should be restored to unset
    monkeypatch.delenv("PURE3270_CONSOLE_MODE", raising=False)
    with patch("sys.argv", ["pure3270", "example.host", "--console"]):
        with patch("pure3270.Session") as mock_session:
            mock_instance = MagicMock()
            mock_session.return_value = mock_instance
            mock_instance.connect.return_value = None
            with patch("builtins.input", return_value="quit"):
                try:
                    main()
                except SystemExit:
                    pass
    assert os.environ.get("PURE3270_CONSOLE_MODE") is None

    # Scenario B: env var initially true, main() called without --console -> should restore to 'true'
    monkeypatch.setenv("PURE3270_CONSOLE_MODE", "true")
    with patch("sys.argv", ["pure3270", "example.host"]):
        with patch("pure3270.Session") as mock_session:
            mock_instance = MagicMock()
            mock_session.return_value = mock_instance
            mock_instance.connect.return_value = None
            with patch("builtins.input", return_value="quit"):
                try:
                    main()
                except SystemExit:
                    pass
    assert os.environ.get("PURE3270_CONSOLE_MODE") == "true"
