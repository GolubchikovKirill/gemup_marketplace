import asyncio
from app.models.models import ProxyProduct, ProxyType, SessionType, ProviderType
from app.core.db import get_db

async def create_test_data():
    async for db in get_db():
        products = [
            ProxyProduct(
                name='US HTTP Proxies - New York',
                description='High-speed HTTP proxies from New York datacenter',
                proxy_type=ProxyType.HTTP,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code='US',
                country_name='United States',
                city='New York',
                price_per_proxy=1.50,
                duration_days=30,
                min_quantity=1,
                max_quantity=100,
                stock_available=500
            ),
            ProxyProduct(
                name='UK SOCKS5 Proxies - London',
                description='Premium SOCKS5 proxies from London',
                proxy_type=ProxyType.SOCKS5,
                session_type=SessionType.STICKY,
                provider=ProviderType.PROVIDER_711,
                country_code='GB',
                country_name='United Kingdom',
                city='London',
                price_per_proxy=2.00,
                duration_days=30,
                min_quantity=1,
                max_quantity=50,
                stock_available=200,
                is_featured=True
            ),
            ProxyProduct(
                name='DE HTTP Proxies - Berlin',
                description='German HTTP proxies for EU traffic',
                proxy_type=ProxyType.HTTP,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code='DE',
                country_name='Germany',
                city='Berlin',
                price_per_proxy=1.75,
                duration_days=30,
                min_quantity=1,
                max_quantity=75,
                stock_available=300
            )
        ]
        
        for product in products:
            db.add(product)
        
        await db.commit()
        print(f'✅ Created {len(products)} test products!')
        break

if __name__ == "__main__":
    asyncio.run(create_test_data())
