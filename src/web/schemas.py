from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from src.core.models.point import ProblemType, Priority, TeamType

class ProblemTypeSchema(str, Enum):
    buraco_asfalto = "buraco_asfalto"
    vazamento_agua = "vazamento_agua"
    vazamento_esgoto = "vazamento_esgoto"
    poste_sem_luz = "poste_sem_luz"
    fiacao_exposta = "fiacao_exposta"
    bueiro_entupido = "bueiro_entupido"
    calcada_quebrada = "calcada_quebrada"
    semaforo_defeito = "semaforo_defeito"

class PrioritySchema(str, Enum):
    emergencia = "emergencia"
    urgente = "urgente"
    alta = "alta"
    media = "media"
    baixa = "baixa"

class TeamTypeSchema(str, Enum):
    asfalto = "asfalto"
    hidraulica = "hidraulica"
    eletrica = "eletrica"
    saneamento = "saneamento"
    geral = "geral"

class PointCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=5, max_length=500)
    problem_type: ProblemTypeSchema
    priority: Priority
    team_type: TeamTypeSchema
    problem_size: str = Field(default="medio", pattern="^(pequeno|medio|grande)$") 
    estimated_time: int = Field(default=30, ge=5, le=480)
    neighborhood: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=50)
    main_road: bool = False
    complaints_count: int = Field(default=0, ge=0)
    affects_traffic: bool = False
    affects_commerce: bool = False
    near_critical: bool = False
    requires_road_block: bool = False
    dependencies: List[str] = []
    materials: List[str] = []
    observations: Optional[str] = ""
    photos: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": -10.965490,
                "longitude": -37.057259,
                "address": "Rua Principal, 123",
                "problem_type": "buraco_asfalto",
                "priority": "emergencia",
                "team_type": "asfalto",
                "problem_size": "grande",
                "estimated_time": 45,
                "neighborhood": "Centro",
                "region": "Centro",
                "main_road": True,
                "complaints_count": 15,
                "affects_traffic": True
            }
        }

class PointUpdate(BaseModel):
    priority: Optional[PrioritySchema] = None
    estimated_time: Optional[int] = Field(None, ge=5, le=480)
    complaints_count: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(aberto|em_andamento|resolvido|cancelado)$")
    observations: Optional[str] = None

class RouteRequest(BaseModel):
    team_type: TeamType
    max_hours: int = Field(default=8, ge=1, le=12)
    max_points: int = Field(default=50, ge=1, le=200)
    date: Optional[date] = None
    point_ids: Optional[List[str]] = None
    start_latitude: Optional[float] = Field(None, ge=-90, le=90)
    start_longitude: Optional[float] = Field(None, ge=-180, le=180)
    strategy: str = Field(default="mixed", pattern="^(priority|geographic|mixed)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "team_type": "asfalto",
                "max_hours": 8,
                "max_points": 30,
                "strategy": "mixed"
            }
        }

# Response Schemas
class PointResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    address: str
    problem_type: str
    priority: str
    team_type: str
    estimated_time: int
    urgency_score: float
    neighborhood: str
    complaints_count: int 
    status: str = "aberto"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RouteResponse(BaseModel):
    team_type: str
    route: List[Dict[str, Any]]
    total_distance_km: float
    total_time_minutes: int
    statistics: Dict[str, Any]
    optimization_time_seconds: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "team_type": "asfalto",
                "route": [
                    {
                        "id": "1",
                        "address": "Rua A, 123",
                        "priority": "emergencia",
                        "estimated_time": 45
                    }
                ],
                "total_distance_km": 15.7,
                "total_time_minutes": 380,
                "statistics": {
                    "total_points": 8,
                    "emergencies": 2,
                    "complaints_resolved": 45
                }
            }
        }

class OptimizationStats(BaseModel):
    total_points: int
    open_points: int
    resolved_points: int
    emergencies: int
    urgent: int
    neighborhoods_covered: int
    avg_resolution_time: float
    total_complaints: int
    optimization_efficiency: float
    
class BatchRouteRequest(BaseModel):
    teams: Dict[str, int]  
    max_hours: int = 8
    date: date
    strategy: str = "mixed"
    
    class Config:
        json_schema_extra = {
            "example": {
                "teams": {
                    "asfalto": 2,
                    "hidraulica": 1,
                    "eletrica": 1
                },
                "max_hours": 8,
                "date": "2024-01-15",
                "strategy": "mixed"
            }
        }

class BatchRouteResponse(BaseModel):
    date: date
    teams_scheduled: Dict[str, List[List[Dict]]]
    total_points_scheduled: int
    total_distance_all_teams: float
    efficiency_metrics: Dict[str, float]

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None