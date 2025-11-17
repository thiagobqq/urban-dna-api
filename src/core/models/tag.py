from dataclasses import dataclass, field
from enum import Enum
from typing import Set, Optional, Dict, Any, List
from datetime import datetime

class TagLevel(Enum):
    PRIORITY = 0   
    TEAM_TYPE = 1    
    LOCATION = 2   
    IMPACT = 3      
    RESOURCE = 4     

class TagWeight(Enum):
    HIGH = 1.0
    MEDIUM = 0.5
    LOW = 0.2

@dataclass
class Tag:
    id: str
    name: str
    level: TagLevel
    weight: float = 1.0
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.id == other.id
        return False
    
    def __repr__(self):
        return f"Tag({self.name}, level={self.level.name})"

@dataclass
class TagGroup:
    id: str
    name: str
    tags: Set[Tag] = field(default_factory=set)
    level: TagLevel = TagLevel.LOCATION
    
    def add_tag(self, tag: Tag):
        if tag.level == self.level:
            self.tags.add(tag)
        else:
            raise ValueError(f"Tag level {tag.level} doesn't match group level {self.level}")
    
    def remove_tag(self, tag: Tag):
        self.tags.discard(tag)
    
    def get_weight(self) -> float:
        if not self.tags:
            return 0.0
        return sum(tag.weight for tag in self.tags) / len(self.tags)

class TagManager:
    
    def __init__(self):
        self.tags: Dict[str, Tag] = {}
        self.groups: Dict[str, TagGroup] = {}
        self._initialize_default_tags()
    
    def _initialize_default_tags(self):
        priority_tags = [
            Tag("P001", "Emergência", TagLevel.PRIORITY, weight=5.0),
            Tag("P002", "Urgente", TagLevel.PRIORITY, weight=4.0),
            Tag("P003", "Alta", TagLevel.PRIORITY, weight=3.0),
            Tag("P004", "Média", TagLevel.PRIORITY, weight=2.0),
            Tag("P005", "Baixa", TagLevel.PRIORITY, weight=1.0),
        ]
        
        team_tags = [
            Tag("T001", "Asfalto", TagLevel.TEAM_TYPE, weight=1.0),
            Tag("T002", "Hidráulica", TagLevel.TEAM_TYPE, weight=1.0),
            Tag("T003", "Elétrica", TagLevel.TEAM_TYPE, weight=1.0),
            Tag("T004", "Saneamento", TagLevel.TEAM_TYPE, weight=1.0),
            Tag("T005", "Geral", TagLevel.TEAM_TYPE, weight=0.5),
        ]
        
        location_tags = [
            Tag("L001", "Centro", TagLevel.LOCATION, weight=1.5),
            Tag("L002", "Zona Norte", TagLevel.LOCATION, weight=1.0),
            Tag("L003", "Zona Sul", TagLevel.LOCATION, weight=1.0),
            Tag("L004", "Zona Leste", TagLevel.LOCATION, weight=1.0),
            Tag("L005", "Zona Oeste", TagLevel.LOCATION, weight=1.0),
        ]
        
        impact_tags = [
            Tag("I001", "Via Principal", TagLevel.IMPACT, weight=2.0),
            Tag("I002", "Próximo a Hospital", TagLevel.IMPACT, weight=3.0),
            Tag("I003", "Próximo a Escola", TagLevel.IMPACT, weight=2.5),
            Tag("I004", "Área Comercial", TagLevel.IMPACT, weight=2.0),
            Tag("I005", "Área Residencial", TagLevel.IMPACT, weight=1.0),
        ]
        
        all_tags = priority_tags + team_tags + location_tags + impact_tags
        for tag in all_tags:
            self.add_tag(tag)
    
    def add_tag(self, tag: Tag):
        self.tags[tag.id] = tag
    
    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self.tags.get(tag_id)
    
    def create_group(self, group_id: str, name: str, level: TagLevel) -> TagGroup:
     
        group = TagGroup(group_id, name, level=level)
        self.groups[group_id] = group
        return group
    
    def calculate_similarity(self, tags1: Set[Tag], tags2: Set[Tag]) -> float:
       
        if not tags1 or not tags2:
            return 0.0
        
        common_tags = tags1.intersection(tags2)
        if not common_tags:
            return 0.0
        
        similarity = 0.0
        for tag in common_tags:
            level_weight = {
                TagLevel.PRIORITY: 0.4,
                TagLevel.TEAM_TYPE: 0.3,
                TagLevel.LOCATION: 0.2,
                TagLevel.IMPACT: 0.1,
                TagLevel.RESOURCE: 0.05
            }.get(tag.level, 0.05)
            
            similarity += tag.weight * level_weight
        
        max_similarity = min(len(tags1), len(tags2))
        return min(similarity / max_similarity, 1.0)
    
    def get_tags_by_level(self, level: TagLevel) -> List[Tag]:
        return [tag for tag in self.tags.values() if tag.level == level]
    
    def suggest_tags(self, existing_tags: Set[Tag]) -> List[Tag]:
       
        suggestions = []
        
        existing_levels = {tag.level for tag in existing_tags}
        
        for level in TagLevel:
            if level not in existing_levels:
                level_tags = self.get_tags_by_level(level)
                if level_tags:
                    suggestions.append(max(level_tags, key=lambda t: t.weight))
        
        return suggestions