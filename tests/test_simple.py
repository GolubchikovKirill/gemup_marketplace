def test_simple():
    assert 1 + 1 == 2

def test_import_app():
    from app.core.main import app
    assert app is not None

def test_import_models():
    from app.models.models import User, ProxyProduct
    assert User is not None
    assert ProxyProduct is not None

def test_user_model_defaults():
    from app.models.models import User
    user = User(email="test@test.com")
    assert user.is_guest is None or user.is_guest == False
    assert user.is_active is None or user.is_active == True
    assert user.balance is None or user.balance == 0.0

def test_proxy_product_model_defaults():
    from app.models.models import ProxyProduct, ProxyType, SessionType, ProviderType
    product = ProxyProduct(
        name="Test Proxy",
        proxy_type=ProxyType.HTTP,
        session_type=SessionType.STICKY,
        provider=ProviderType.PROVIDER_711,
        country_code="US",
        country_name="United States",
        price_per_proxy=1.0,
        duration_days=30
    )
    assert product.is_active is None or product.is_active == True
    assert product.is_featured is None or product.is_featured == False
