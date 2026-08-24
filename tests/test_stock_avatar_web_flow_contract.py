from services.stock_avatar_web_service import StockAvatarWebService


def test_browser_contract_limits_are_explicit() -> None:
    service = StockAvatarWebService()
    assert service.MAX_CLIPS == 6
    assert service.MAX_TOPIC_LENGTH == 500
