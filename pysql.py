#!/usr/bin/env python3
# pip install duckdb sqlalchemy pymssql pyodbc pandas tabulate openpyxl
"""
PySql - Cliente SQL multi-base de datos
Soporta: DuckDB, SQL Server (MSSQL)

Requisitos:
  - DuckDB: pip install duckdb
  - MSSQL:  pip install sqlalchemy pymssql pyodbc
  - Común:  pip install pandas tabulate
"""

import argparse
import sys
import os
import pandas as pd
from typing import Optional
from urllib.parse import quote_plus

class DuckDBClient:
    """Cliente para DuckDB"""
    def __init__(self, database: str):
        self.database = database
        self.connection = None

    def connect(self) -> bool:
        try:
            import duckdb
            self.connection = duckdb.connect(self.database, read_only=False)
            print(f"✓ Conectado a DuckDB: {self.database}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"✗ Error conectando a DuckDB: {str(e)}", file=sys.stderr)
            return False

    def execute_query(self, query: str, output_format: str = "table") -> bool:
        if not self.connection:
            print("Error: No hay conexión activa", file=sys.stderr)
            return False

        try:
            queries = [q.strip() for q in query.split(';') if q.strip()]

            for q in queries:
                if not q:
                    continue

                print(f"Ejecutando: {self._truncate(q, 60)}", file=sys.stderr)

                result = self.connection.execute(q)

                if self._is_select(q):
                    df = result.fetchdf()
                    self._output(df, output_format)
                else:
                    print(f"Comando ejecutado", file=sys.stderr)
                print()

            return True
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return False

    def _is_select(self, query: str) -> bool:
        q = query.strip().upper()
        return q.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'PRAGMA'))

    def _output(self, df: pd.DataFrame, fmt: str):
        if df.empty:
            print("(0 filas)")
            return

        if fmt == "csv":
            df.to_csv(sys.stdout, index=False)
        elif fmt == "json":
            print(df.to_json(orient='records', indent=2))
        elif fmt == "excel":
            filename = f"resultado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            print(f"Guardado en: {filename}")
        else:
            try:
                from tabulate import tabulate
                print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
            except ImportError:
                print(df.to_string(index=False))

        print(f"\n({len(df)} filas)", file=sys.stderr)

    def _truncate(self, s: str, max_len: int) -> str:
        s = ' '.join(s.split())
        return s[:max_len] + '...' if len(s) > max_len else s

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None


class MSSQLClient:
    """Cliente para SQL Server"""
    def __init__(self, server: str, port: int, user: str = None, password: str = None,
                 database: str = "master", trusted: bool = False):
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.trusted = trusted
        self.engine = None
        self.connection = None

    def connect(self) -> bool:
        try:
            from sqlalchemy import create_engine

            if self.trusted:
                # Conexión trusted usando pyodbc
                conn_str = (
                    f"mssql+pyodbc://@{self.server}:{self.port}/{self.database}"
                    f"?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
                    f"&Trusted_Connection=yes"
                )
                auth_type = "Windows Auth"
            else:
                # Conexión con usuario/password usando pymssql
                password_encoded = quote_plus(self.password) if self.password else ''
                conn_str = f"mssql+pymssql://{self.user}:{password_encoded}@{self.server}:{self.port}/{self.database}"
                auth_type = f"SQL Auth ({self.user})"

            self.engine = create_engine(conn_str, echo=False)
            self.connection = self.engine.connect()
            print(f"✓ Conectado a MSSQL: {self.server}:{self.port}/{self.database} [{auth_type}]", file=sys.stderr)
            return True
        except Exception as e:
            print(f"✗ Error conectando a MSSQL: {str(e)}", file=sys.stderr)
            return False

    def execute_query(self, query: str, output_format: str = "table") -> bool:
        if not self.connection:
            print("Error: No hay conexión activa", file=sys.stderr)
            return False

        try:
            from sqlalchemy import text

            # Dividir por GO o punto y coma
            if 'GO' in query.upper():
                queries = [q.strip() for q in query.split('GO') if q.strip()]
            else:
                queries = [q.strip() for q in query.split(';') if q.strip()]

            for q in queries:
                if not q:
                    continue

                print(f"Ejecutando: {self._truncate(q, 60)}", file=sys.stderr)

                if self._is_select(q):
                    df = pd.read_sql(text(q), self.connection)
                    self._output(df, output_format)
                else:
                    result = self.connection.execute(text(q))
                    if hasattr(result, 'rowcount') and result.rowcount >= 0:
                        print(f"Filas afectadas: {result.rowcount}")
                    self.connection.commit()
                print()

            return True
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return False

    def _is_select(self, query: str) -> bool:
        q = query.strip().upper()
        return q.startswith(('SELECT', 'WITH', 'SHOW', 'EXEC', 'EXECUTE', 'SP_'))

    def _output(self, df: pd.DataFrame, fmt: str):
        if df.empty:
            print("(0 filas)")
            return

        if fmt == "csv":
            df.to_csv(sys.stdout, index=False)
        elif fmt == "json":
            print(df.to_json(orient='records', indent=2))
        elif fmt == "excel":
            filename = f"resultado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            print(f"Guardado en: {filename}")
        else:
            try:
                from tabulate import tabulate
                print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
            except ImportError:
                print(df.to_string(index=False))

        print(f"\n({len(df)} filas)", file=sys.stderr)

    def _truncate(self, s: str, max_len: int) -> str:
        s = ' '.join(s.split())
        return s[:max_len] + '...' if len(s) > max_len else s

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None


def main():
    parser = argparse.ArgumentParser(
        description="Cliente SQL multi-base de datos (DuckDB, MSSQL)",
        epilog="""
Ejemplos DuckDB:
  pysql.py --duckdb censo.duckdb -Q "SELECT * FROM personas LIMIT 5"
  pysql.py --duckdb censo.duckdb -i consulta.sql -o csv

Ejemplos MSSQL (SQL Auth):
  pysql.py -S servidor -U usuario -p password -Q "SELECT @@VERSION"
  pysql.py -S servidor -U sa -p mipass -d midb -i query.sql -o csv

Ejemplos MSSQL (Windows Auth):
  pysql.py -S servidor -T -Q "SELECT @@VERSION"
  pysql.py -S servidor -T -d midb -i query.sql
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Grupo DuckDB
    duck_group = parser.add_argument_group('DuckDB')
    duck_group.add_argument('--duckdb', metavar='FILE', help='Archivo DuckDB a conectar')

    # Grupo MSSQL
    mssql_group = parser.add_argument_group('SQL Server')
    mssql_group.add_argument('-S', '--server', help='Servidor SQL')
    mssql_group.add_argument('-P', '--port', type=int, default=1433, help='Puerto (default: 1433)')
    mssql_group.add_argument('-U', '--user', help='Usuario')
    mssql_group.add_argument('-p', '--password', default='', help='Contraseña')
    mssql_group.add_argument('-d', '--database', default='master', help='Base de datos')
    mssql_group.add_argument('-T', '--trusted', action='store_true',
                            help='Usar Windows Authentication (trusted connection)')

    # Opciones comunes
    parser.add_argument('-Q', '--query', help='Query SQL a ejecutar')
    parser.add_argument('-i', '--input-file', help='Archivo SQL a ejecutar')
    parser.add_argument('-o', '--output', choices=['table', 'csv', 'json', 'excel'],
                       default='table', help='Formato de salida')

    args = parser.parse_args()

    # Validar modo de conexión
    if args.duckdb and args.server:
        print("Error: Use --duckdb o -S, no ambos", file=sys.stderr)
        sys.exit(1)

    if not args.duckdb and not args.server:
        print("Error: Especifique --duckdb FILE o -S servidor", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Validar query
    if not args.query and not args.input_file:
        print("Error: Especifique -Q (query) o -i (archivo)", file=sys.stderr)
        sys.exit(1)

    if args.query and args.input_file:
        print("Error: Use solo -Q o -i, no ambos", file=sys.stderr)
        sys.exit(1)

    # Obtener query
    if args.input_file:
        if not os.path.exists(args.input_file):
            print(f"Error: Archivo '{args.input_file}' no existe", file=sys.stderr)
            sys.exit(1)
        with open(args.input_file, 'r', encoding='utf-8') as f:
            query = f.read()
    else:
        query = args.query

    # Crear cliente según el tipo
    if args.duckdb:
        if not os.path.exists(args.duckdb):
            print(f"Error: Archivo '{args.duckdb}' no existe", file=sys.stderr)
            sys.exit(1)
        client = DuckDBClient(args.duckdb)
    else:
        if not args.trusted and not args.user:
            print("Error: Se requiere -U (usuario) o -T (trusted) para MSSQL", file=sys.stderr)
            sys.exit(1)
        client = MSSQLClient(args.server, args.port, args.user, args.password,
                            args.database, args.trusted)

    # Ejecutar
    try:
        if not client.connect():
            sys.exit(1)
        if not client.execute_query(query, args.output):
            sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
