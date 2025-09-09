import pytest
import sys
from unittest.mock import patch, MagicMock
from pure3270 import main


def test_main_no_args(capsys):
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


def test_main_with_host(capsys):
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


def test_main_with_script(capsys):
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
                mock_instance.execute_macro.return_value = {"success": True}
                main()
                captured = capsys.readouterr()
                assert "Script executed" in captured.out
