import sys


from unittest.mock import patch, AsyncMock

from main import main


@patch("main.check_retrieved_transcriptions")
@patch("main.get_transcription_youtube", new_callable=AsyncMock)
@patch("main.initialise_database")
@patch("main.build_vault_map")
def test_pipeline_full_flow(
    mock_build_vault,
    mock_init_db,
    mock_get,
    mock_check,
):
    mock_check.return_value = None
    mock_get.return_value = "integrated transcript"
    mock_build_vault.return_value = {}

    with patch("sys.argv", ["script.py", "https://youtu.be/123"]):
        main(sys.argv)

    mock_build_vault.assert_called_once()
    mock_init_db.assert_called_once()
    mock_check.assert_called_once_with("https://youtu.be/123")
    mock_get.assert_called_once_with("https://youtu.be/123")
