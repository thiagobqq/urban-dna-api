from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

class ProblemType(Enum):
    BURACO_ASFALTO = "buraco_asfalto"
    VAZAMENTO_AGUA = "vazamento_agua"
    VAZAMENTO_ESGOTO = "vazamento_esgoto"
    POSTE_SEM_LUZ = "poste_sem_luz"
    FIACAO_EXPOSTA = "fiacao_exposta"
    BUEIRO_ENTUPIDO = "bueiro_entupido"
    CALCADA_QUEBRADA = "calcada_quebrada"
    SEMAFORO_DEFEITO = "semaforo_defeito"

class Priority(Enum):
    EMERGENCIA = 5
    URGENTE = 4
    ALTA = 3
    MEDIA = 2
    BAIXA = 1

class TeamType(Enum):
    ASFALTO = "asfalto"
    HIDRAULICA = "hidraulica"
    ELETRICA = "eletrica"
    SANEAMENTO = "saneamento"
    GERAL = "geral"

@dataclass(frozen=True)
class MaintenancePoint:

    latitude: float
    longitude: float
    address: str
    
    # Problema
    problem_type: ProblemType
    priority: Priority
    team_type: TeamType
    problem_size: str
    estimated_time: int 
    
    neighborhood: str
    region: str
    
    id: Optional[str] = field(default=None)

    main_road: bool = False
    
    complaints_count: int = 0
    affects_traffic: bool = False
    affects_commerce: bool = False
    near_critical: bool = False

    requires_road_block: bool = False
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    materials: Tuple[str, ...] = field(default_factory=tuple)
    photos: Tuple[str, ...] = field(default_factory=tuple)
    
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "aberto"
    observations: str = ""
    

    @property
    def coordinates(self) -> tuple:
        return (self.latitude, self.longitude)
    
    @property
    def urgency_score(self) -> float:
        score = self.priority.value * 100
        score += self.complaints_count * 10
        
        if self.near_critical:
            score += 50
        if self.main_road:
            score += 30
        if self.affects_traffic:
            score += 25
        if self.affects_commerce:
            score += 20
        
        if self.estimated_time > 120:
            score *= 0.8
            
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "problem_type": self.problem_type.value,
            "priority": self.priority.name,
            "team_type": self.team_type.value,
            "estimated_time": self.estimated_time,
            "urgency_score": self.urgency_score,
            "neighborhood": self.neighborhood,
            "complaints": self.complaints_count
        }