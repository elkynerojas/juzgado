from alembic import context

from app.server.db.models import Base
from app.server.db.session import crear_engine

target_metadata = Base.metadata


def _migrar(conexion) -> None:
    # render_as_batch: SQLite no soporta ALTER TABLE completo
    context.configure(connection=conexion, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


conexion = context.config.attributes.get("connection")
if conexion is not None:
    _migrar(conexion)
else:
    with crear_engine().connect() as conexion:
        _migrar(conexion)
        conexion.commit()
