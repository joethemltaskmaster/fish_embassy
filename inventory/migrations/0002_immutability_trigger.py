from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION inventory_stockmovement_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'StockMovement rows are append-only (attempted %)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_stockmovement_no_update
    BEFORE UPDATE ON inventory_stockmovement
    FOR EACH ROW EXECUTE FUNCTION inventory_stockmovement_immutable();

CREATE TRIGGER inventory_stockmovement_no_delete
    BEFORE DELETE ON inventory_stockmovement
    FOR EACH ROW EXECUTE FUNCTION inventory_stockmovement_immutable();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS inventory_stockmovement_no_update ON inventory_stockmovement;
DROP TRIGGER IF EXISTS inventory_stockmovement_no_delete ON inventory_stockmovement;
DROP FUNCTION IF EXISTS inventory_stockmovement_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]