import asyncio
from app.main import app
from app.core.database import engine, Base

async def test_lifespan():
    print("Testando Inicialização do Banco...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Banco de dados inicializado OK")
    except Exception as e:
        print(f"ERRO NO BANCO: {e}")
        return

    print("Testando Startup Tasks...")
    from app.services.data_collector import data_collector
    from app.services.automation_service import automation_service
    
    try:
        # Tenta iniciar os serviços e cancela logo depois
        collector_task = asyncio.create_task(data_collector.start_loop())
        automation_task = asyncio.create_task(automation_service.start())
        print("Tasks iniciadas...")
        await asyncio.sleep(2)
        collector_task.cancel()
        automation_task.cancel()
        print("Lifespan test concluído sem crash fatal imediato")
    except Exception as e:
        print(f"ERRO NAS TASKS: {e}")

if __name__ == "__main__":
    asyncio.run(test_lifespan())
