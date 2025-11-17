import asyncio
import asyncpg
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from contextlib import asynccontextmanager

from src.core.models.point import MaintenancePoint, Priority, ProblemType, TeamType
from src.core.models.tag import Tag, TagLevel

class Database:
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            timeout=60,
            command_timeout=60
        )
    
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def acquire(self):
        async with self.pool.acquire() as connection:
            yield connection
    
    async def init_db(self):
        async with self.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'maintenance_points')"
            )
            
            if not exists:
                print("Criando estrutura do banco de dados...")
                with open('init.sql', 'r') as f:
                    await conn.execute(f.read())
                print("Banco de dados inicializado com sucesso!")
    
    
   

    async def create_point(self, point: MaintenancePoint) -> str:
        async with self.acquire() as conn:
            point_id = await conn.fetchval(
                """
                INSERT INTO maintenance_points (
                    latitude, longitude, location, address, neighborhood, region,
                    problem_type, priority, team_type, problem_size, 
                    estimated_time_minutes, complaints_count,
                    affects_traffic, affects_commerce, near_critical_location, 
                    main_road, status, requires_road_block,
                    dependencies, materials, photos, observations, metadata,
                    urgency_score
                ) VALUES (
                    $1::DECIMAL, $2::DECIMAL, 
                    ST_MakePoint($2, $1)::geography, $3, $4, $5,
                    $6::problem_type, $7::priority_level, $8::team_type, $9, 
                    $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22,
                    $23::DECIMAL
                ) RETURNING id
                """,
                point.latitude, point.longitude, point.address, 
                point.neighborhood, point.region,
                point.problem_type.value, point.priority.name.lower(), 
                point.team_type.value, point.problem_size,
                point.estimated_time, point.complaints_count,
                point.affects_traffic, point.affects_commerce, 
                point.near_critical, point.main_road,
                point.status, point.requires_road_block,
                point.dependencies, json.dumps(point.materials),
                json.dumps(point.photos), point.observations,
                json.dumps({}),
                point.urgency_score
            )
            return str(point_id)
        
    async def get_point(self, point_id: str) -> Optional[MaintenancePoint]:
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM maintenance_points WHERE id = $1
                """,
                point_id
            )
            
            if row:
                return self._row_to_point(row)
            return None
    
    async def get_points(self, 
                        team_type: Optional[TeamType] = None,
                        priority: Optional[Priority] = None,
                        status: str = "aberto",
                        limit: int = 100) -> List[MaintenancePoint]:
        async with self.acquire() as conn:
            query = """
                SELECT * FROM maintenance_points 
                WHERE status = $1
            """
            params = [status]
            param_count = 1
            
            if team_type:
                param_count += 1
                query += f" AND team_type = ${param_count}::team_type"
                params.append(team_type.value)
            
            if priority:
                param_count += 1
                query += f" AND priority = ${param_count}::priority_level"
                params.append(priority.name.lower())
            
            query += f" ORDER BY priority DESC LIMIT ${param_count + 1}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            return [self._row_to_point(row) for row in rows]
    
    async def update_point_status(self, point_id: str, status: str):
        async with self.acquire() as conn:
            await conn.execute(
                """
                UPDATE maintenance_points 
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
                """,
                status, point_id
            )
    
    async def get_points_by_neighborhood(self, neighborhood: str) -> List[MaintenancePoint]:
        
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM maintenance_points 
                WHERE neighborhood = $1 AND status = 'aberto'
                ORDER BY priority DESC
                """,
                neighborhood
            )
            
            return [self._row_to_point(row) for row in rows]
    
    async def get_nearby_points(self, lat: float, lon: float, radius_km: float = 5) -> List[MaintenancePoint]:
    
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *, 
                       ST_Distance(location, ST_MakePoint($2, $1)::geography) / 1000 as distance_km
                FROM maintenance_points
                WHERE ST_DWithin(
                    location, 
                    ST_MakePoint($2, $1)::geography, 
                    $3 * 1000
                )
                AND status = 'aberto'
                ORDER BY distance_km
                """,
                lat, lon, radius_km
            )
            
            return [self._row_to_point(row) for row in rows]
    
    
    async def get_cached_distance(self, point_a_id: str, point_b_id: str) -> Optional[float]:
        async with self.acquire() as conn:
            distance = await conn.fetchval(
                """
                SELECT distance_km FROM distance_cache
                WHERE (point_a_id = $1 AND point_b_id = $2)
                   OR (point_a_id = $2 AND point_b_id = $1)
                """,
                point_a_id, point_b_id
            )
            return distance
    
    async def cache_distance(self, point_a_id: str, point_b_id: str, distance_km: float):

        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO distance_cache (point_a_id, point_b_id, distance_km)
                VALUES ($1, $2, $3)
                ON CONFLICT (point_a_id, point_b_id) DO UPDATE
                SET distance_km = $3, calculated_at = CURRENT_TIMESTAMP
                """,
                point_a_id, point_b_id, distance_km
            )
    
    
    async def save_route(self, route_data: Dict[str, Any]):
        async with self.acquire() as conn:
            route_id = await conn.fetchval(
                """
                INSERT INTO optimized_routes (
                    team_type, route_date, total_points,
                    total_distance_km, total_time_minutes,
                    route_order, statistics
                ) VALUES ($1::team_type, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                route_data['team_type'], route_data['date'],
                route_data['total_points'], route_data['total_distance'],
                route_data['total_time'], json.dumps(route_data['route_order']),
                json.dumps(route_data['statistics'])
            )
            return str(route_id)
    
    async def get_routes_history(self, team_type: Optional[TeamType] = None, 
                                days: int = 30) -> List[Dict]:
        async with self.acquire() as conn:
            query = """
                SELECT * FROM optimized_routes
                WHERE route_date >= CURRENT_DATE - INTERVAL '%s days'
            """
            params = [days]
            
            if team_type:
                query += " AND team_type = $2::team_type"
                params.append(team_type.value)
            
            query += " ORDER BY created_at DESC"
            
            rows = await conn.fetch(query, *params)
            
            return [dict(row) for row in rows]
    
    
    async def get_statistics(self) -> Dict[str, Any]:
        async with self.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_points,
                    COUNT(CASE WHEN status = 'aberto' THEN 1 END) as open_points,
                    COUNT(CASE WHEN status = 'resolvido' THEN 1 END) as resolved_points,
                    COUNT(CASE WHEN priority = 'emergencia' THEN 1 END) as emergencies,
                    COUNT(CASE WHEN priority = 'urgente' THEN 1 END) as urgent,
                    COUNT(DISTINCT neighborhood) as neighborhoods,
                    AVG(estimated_time_minutes) as avg_time_minutes,
                    SUM(complaints_count) as total_complaints
                FROM maintenance_points
                """
            )
            
            return dict(stats)
        
    
    def _row_to_point(self, row) -> MaintenancePoint:
        return MaintenancePoint(
            id=str(row['id']),
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            address=row['address'],
            problem_type=ProblemType(row['problem_type']),
            priority=Priority[row['priority'].upper()],
            team_type=TeamType(row['team_type']),
            problem_size=row['problem_size'],
            estimated_time=row['estimated_time_minutes'],
            neighborhood=row['neighborhood'],
            region=row['region'],
            main_road=row['main_road'],
            complaints_count=row['complaints_count'],
            affects_traffic=row['affects_traffic'],
            affects_commerce=row['affects_commerce'],
            near_critical=row['near_critical_location'],
            requires_road_block=row['requires_road_block'],
            dependencies=tuple(row['dependencies']) if row['dependencies'] else (),
            materials=tuple(json.loads(row['materials'])) if row['materials'] else (),
            photos=tuple(json.loads(row['photos'])) if row['photos'] else (),
            status=row['status'],
            observations=row['observations'] or "",
            created_at=row['created_at']
        )

_database: Optional[Database] = None

async def get_database() -> Database:
    global _database
    if _database is None:
        import os
        database_url = os.getenv('DATABASE_URL', 'postgresql://admin:admin123@localhost:5432/urban_maintenance')
        _database = Database(database_url)
        await _database.connect()
    return _database

async def init_db():
    db = await get_database()
    await db.init_db()