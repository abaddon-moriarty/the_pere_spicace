"""
Integration tests for the complete pipeline.
"""

import sys


from unittest.mock import patch

sys.path.insert(0, "transcription_client")


class TestFullPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_end_to_end_with_mocks(self):
        """Test the full pipeline with all components mocked."""
        test_args = [
            "main.py",
            "https://www.youtube.com/watch?v=integration_test",
        ]
        mock_transcript = "Integration test transcript."

        # Mock asyncio.run
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_transcript
            with patch("sys.argv", test_args):
                import io

                from contextlib import redirect_stdout

                f = io.StringIO()
                with redirect_stdout(f):
                    from main import main

                    main(test_args)

                output = f.getvalue()

                assert "Starting the Youtube learning pipeline" in output

    def test_error_handling_integration(self):
        """Test error handling through the entire pipeline."""
        test_args = ["main.py", "https://youtube.com/invalid"]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = ""
            with patch("sys.argv", test_args):
                import io

                from contextlib import redirect_stdout

                f = io.StringIO()
                with redirect_stdout(f):
                    from main import main

                    main(test_args)

                output = f.getvalue()
                assert "Starting the Youtube learning pipeline" in output
