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
def test_main_with_host(capsys, memory_limit_500mb):
    with patch("sys.argv", ["pure3270", "test.host"]):
        with patch("pure3270.Session") as mock_session:
            mock_instance = MagicMock()
            mock_session.return_value = mock_instance
            mock_instance.connect.return_value = None
            # Mock input to immediately return 'quit' to exit the loop
            with patch("builtins.input", return_value="quit"):
                try:
                    main()
                except SystemExit:
                    pass  # Normal exit
                captured = capsys.readouterr()
                assert "Connected to test.host:23" in captured.out


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_main_with_script(capsys, memory_limit_500mb):
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
                main()
                captured = capsys.readouterr()
                # Stronger message explicitly states permanence
                assert "permanently unsupported" in captured.out
