"""
Seed initial data for the application
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.user import Role, RoleType
from app.models.subscription import SubscriptionPlan, PlanType


async def seed_roles():
    """Seed default roles"""
    async with AsyncSessionLocal() as db:
        roles = [
            {
                "name": RoleType.ADMIN,
                "display_name": "Administrator",
                "description": "Full access to all features",
            },
            {
                "name": RoleType.MANAGER,
                "display_name": "Manager",
                "description": "Manage operations and view reports",
            },
            {
                "name": RoleType.ANALYST,
                "display_name": "Analyst",
                "description": "View analytics and generate reports",
            },
            {
                "name": RoleType.FINANCE,
                "display_name": "Finance",
                "description": "Manage billing and view financial reports",
            },
        ]

        for role_data in roles:
            role = Role(**role_data)
            db.add(role)

        await db.commit()
        print("✓ Roles seeded successfully")


async def seed_subscription_plans():
    """Seed subscription plans"""
    async with AsyncSessionLocal() as db:
        plans = [
            {
                "name": PlanType.TRIAL,
                "display_name": "Trial",
                "description": "14-day free trial",
                "price": 0,
                "max_channels": 1,
                "max_orders_per_month": 50,
                "max_users": 2,
            },
            {
                "name": PlanType.STARTER,
                "display_name": "Starter",
                "description": "Perfect for small businesses",
                "price": 2999,
                "max_channels": 2,
                "max_orders_per_month": 500,
                "max_users": 5,
            },
            {
                "name": PlanType.GROWTH,
                "display_name": "Growth",
                "description": "For growing D2C brands",
                "price": 7999,
                "max_channels": 5,
                "max_orders_per_month": 2000,
                "max_users": 10,
            },
            {
                "name": PlanType.PROFESSIONAL,
                "display_name": "Professional",
                "description": "Unlimited features for established brands",
                "price": 19999,
                "max_channels": 999,
                "max_orders_per_month": 999999,
                "max_users": 50,
            },
        ]

        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)

        await db.commit()
        print("✓ Subscription plans seeded successfully")


async def seed_hsn_codes():
    """Seed common HSN codes"""
    from app.models.product import HSNCode

    async with AsyncSessionLocal() as db:
        hsn_codes = [
            {
                "code": "6109",
                "description": "T-shirts, singlets and other vests, knitted or crocheted",
                "cgst_rate": 6.0,
                "sgst_rate": 6.0,
                "igst_rate": 12.0,
            },
            {
                "code": "6203",
                "description": "Men's or boys' suits, ensembles, jackets, blazers, trousers",
                "cgst_rate": 6.0,
                "sgst_rate": 6.0,
                "igst_rate": 12.0,
            },
            {
                "code": "8517",
                "description": "Telephone sets, including smartphones and other apparatus",
                "cgst_rate": 9.0,
                "sgst_rate": 9.0,
                "igst_rate": 18.0,
            },
            {
                "code": "3304",
                "description": "Beauty or make-up preparations and preparations for the care of the skin",
                "cgst_rate": 9.0,
                "sgst_rate": 9.0,
                "igst_rate": 18.0,
            },
            {
                "code": "1905",
                "description": "Bread, pastry, cakes, biscuits and other bakers' wares",
                "cgst_rate": 9.0,
                "sgst_rate": 9.0,
                "igst_rate": 18.0,
            },
        ]

        for hsn_data in hsn_codes:
            hsn = HSNCode(**hsn_data)
            db.add(hsn)

        await db.commit()
        print("✓ HSN codes seeded successfully")


async def main():
    """Main seed function"""
    print("Starting data seeding...")

    try:
        await seed_roles()
        await seed_subscription_plans()
        await seed_hsn_codes()
        print("\n✅ All data seeded successfully!")
    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
