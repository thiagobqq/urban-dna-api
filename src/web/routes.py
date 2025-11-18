from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import date
import asyncio
import time

from src.core.models.point import MaintenancePoint, TeamType, Priority, ProblemType
from src.core.algorithms.optimizer import TagBasedOptimizer
from src.infra.database import Database, get_database

from src.web.schemas import (
    PointCreate, 
    PointResponse, 
    RouteRequest, 
    RouteResponse,
    OptimizationStats
)

router = APIRouter()

def calculate_initial_urgency_score(point_data: dict) -> float:
    weights = {
        'priority_base': 100.0, 'complaints': 10.0, 'critical_location': 50.0,
        'main_road': 30.0, 'traffic_impact': 25.0, 'commerce_impact': 20.0,
        'efficiency_penalty': -0.2
    }
    priority_values = {"emergencia": 5, "urgente": 4, "alta": 3, "media": 2, "baixa": 1}
    
    score = 0.0
    priority_str = point_data.get('priority').value
    priority_numeric = priority_values.get(priority_str, 0)
    score += priority_numeric * weights['priority_base']
    
    score += point_data.get('complaints_count', 0) * weights['complaints']
    if point_data.get('near_critical'): score += weights['critical_location']
    if point_data.get('main_road'): score += weights['main_road']
    if point_data.get('affects_traffic'): score += weights['traffic_impact']
    if point_data.get('affects_commerce'): score += weights['commerce_impact']
        
    if point_data.get('estimated_time', 0) > 120:
        penalty = (point_data.get('estimated_time') - 120) * weights['efficiency_penalty']
        score += penalty

    return round(max(0, score), 2)

@router.post("/points", response_model=PointResponse, status_code=201)
async def create_point(point: PointCreate, db: Database = Depends(get_database)):
    point_data = point.model_dump()

    try:
        point_data['priority'] = Priority[point_data['priority'].upper()]
        point_data['team_type'] = TeamType(point_data['team_type'])
        point_data['problem_type'] = ProblemType(point_data['problem_type'])
        db_point_data = MaintenancePoint(**point_data)

        new_point_id = await db.create_point(db_point_data)
        
        created_point = await db.get_point(new_point_id)
        
        if not created_point:
             raise HTTPException(status_code=500, detail="Falha ao recuperar o ponto após a criação.")

    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Valor inválido para enum: {e}")
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Erro de tipo nos dados fornecidos: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao interagir com o banco de dados: {e}")

    return created_point

@router.get("/points", response_model=List[PointResponse])
async def get_points(
    db: Database = Depends(get_database),
    team_type: Optional[TeamType] = None,
    priority: Optional[Priority] = None,
    limit: int = Query(100, le=1000)
):
    points = await db.get_points(
        team_type=team_type,
        priority=priority,
        limit=limit,
        status="aberto"
    )
    return points


@router.post("/optimize", response_model=RouteResponse)
async def optimize_route(request: RouteRequest, db: Database = Depends(get_database)):
    points_to_optimize: List[MaintenancePoint] = []

    if request.point_ids:
        tasks = [db.get_point(point_id) for point_id in request.point_ids]
        results = await asyncio.gather(*tasks)
        points_to_optimize = [p for p in results if p is not None]
    else:
        points_to_optimize = await db.get_points(
            team_type=request.team_type,
            status="aberto",
            limit=500
        )

    if not points_to_optimize:
        raise HTTPException(
            status_code=404,
            detail="Nenhum ponto de manutenção encontrado para os critérios fornecidos."
        )
    start_time = time.time()
    
    optimizer = TagBasedOptimizer(points_to_optimize)
    result = optimizer.optimize_route(
        team_type=request.team_type,
        max_hours=request.max_hours
    )
    
    optimization_time = time.time() - start_time
    
    from src.core.algorithms.distance import haversine_distance
    
    AVERAGE_SPEED_KMH = 30  
    SETUP_TIME_MINUTES = 5  
    
    enriched_route = []
    accumulated_time = 0.0
    accumulated_distance = 0.0
    total_travel_time = 0.0 
    
    for index, point in enumerate(result.route):
        if index > 0:
            prev_point = result.route[index - 1]
            distance_from_prev = haversine_distance(
                prev_point.coordinates, 
                point.coordinates
            )
            travel_time_from_prev = (distance_from_prev / AVERAGE_SPEED_KMH) * 60
            
            accumulated_time += (
                prev_point.estimated_time + 
                travel_time_from_prev + 
                SETUP_TIME_MINUTES
            )
            accumulated_distance += distance_from_prev
            total_travel_time += travel_time_from_prev 
        
        distance_to_next = None
        travel_time_to_next = None
        if index < len(result.route) - 1:
            next_point = result.route[index + 1]
            distance_to_next = round(
                haversine_distance(point.coordinates, next_point.coordinates), 
                2
            )
            travel_time_to_next = round(
                (distance_to_next / AVERAGE_SPEED_KMH) * 60, 
                1
            )
        
        enriched_route.append({
            "stop_number": index + 1,
            "id": point.id,
            "address": point.address,
            "neighborhood": point.neighborhood,
            "priority": point.priority.name,
            "estimated_time": point.estimated_time,
            "arrival_time_minutes": round(accumulated_time, 1),
            "distance_to_next_km": distance_to_next,
            "travel_time_to_next_min": travel_time_to_next,
            "coordinates": point.coordinates,
            "complaints_count": point.complaints_count
        })
    
    total_work_time = sum(p.estimated_time for p in result.route)
    total_setup_time = len(result.route) * SETUP_TIME_MINUTES
    
    total_time_real = total_work_time + total_travel_time + total_setup_time
    
    enhanced_statistics = {
        **result.statistics,
        "total_work_time_minutes": total_work_time,
        "total_travel_time_minutes": round(total_travel_time, 1),
        "total_setup_time_minutes": total_setup_time,
        "total_time_real_minutes": round(total_time_real, 1), 
        "efficiency_points_per_km": round(
            len(result.route) / result.total_distance, 2
        ) if result.total_distance > 0 else 0,
        "avg_time_per_point_minutes": round(
            total_work_time / len(result.route), 1
        ) if result.route else 0,
        "work_time_percentage": round(
            (total_work_time / total_time_real * 100), 1
        ) if total_time_real > 0 else 0,  
        "travel_time_percentage": round(
            (total_travel_time / total_time_real * 100), 1
        ) if total_time_real > 0 else 0,  
    }
    
    max_minutes = request.max_hours * 60
    if total_time_real > max_minutes:
        enhanced_statistics["warning"] = f"Rota excede tempo máximo em {round(total_time_real - max_minutes, 1)} minutos"
    
    return RouteResponse(
        team_type=result.team_type.value,
        route=enriched_route,
        total_distance_km=round(result.total_distance, 2),
        total_time_minutes=int(round(total_time_real, 1)),  
        statistics=enhanced_statistics,
        optimization_time_seconds=round(optimization_time, 3)  
    )
