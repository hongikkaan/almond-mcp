"""Retain retired Sheet records without keeping live object constraints."""


class DrawingsStore:
    def _retire_drawing_sheet_constraints(self, connection) -> None:
        """Preserve legacy rows; fresh projects do not create Sheet tables.

        Retired metadata links must not prevent Component/Scene operations.
        Rebuild only link tables, retaining their original identifiers, inside
        the store initialization transaction.
        """
        for table, field, target in (
            ("drawing_sheet_components", "component_id", "components"),
            ("drawing_sheet_scenes", "scene_id", "scenes"),
        ):
            if not any(row["table"] == target for row in connection.execute(f"PRAGMA foreign_key_list({table})")):
                continue
            temporary = table + "_retired_migration"
            connection.execute(f"""CREATE TABLE {temporary} (
                sheet_id TEXT NOT NULL REFERENCES drawing_sheets(sheet_id) ON DELETE CASCADE,
                {field} TEXT NOT NULL,
                PRIMARY KEY(sheet_id, {field})
            )""")
            connection.execute(f"INSERT INTO {temporary} SELECT sheet_id, {field} FROM {table}")
            connection.execute(f"DROP TABLE {table}")
            connection.execute(f"ALTER TABLE {temporary} RENAME TO {table}")
            connection.execute(f"CREATE INDEX idx_{table}_ref ON {table}({field}, sheet_id)")
