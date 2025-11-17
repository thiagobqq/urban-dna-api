from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import heapq

from src.core.models.point import MaintenancePoint, Priority, TeamType
from src.core.models.tag import Tag, TagManager, TagLevel

@dataclass
class PriorityScore:
    point: MaintenancePoint
    score: float
    factors: Dict[str, float]
    
    def __lt__(self, other):
        return self.score > other.score  

class IntelligentPrioritizer:
    
    def __init__(self, tag_manager: Optional[TagManager] = None):
        self.tag_manager = tag_manager or TagManager()
        self.weights = self._initialize_weights()
    
    def _initialize_weights(self) -> Dict[str, float]:
        return {
            'priority_base': 100.0,    
            'complaints': 10.0,         
            'critical_location': 50.0,              
            'main_road': 30.0,        
            'traffic_impact': 25.0,     
            'commerce_impact': 20.0,    
            'time_waiting': 2.0,        
            'cluster_bonus': 15.0,      
            'same_materials': 10.0,     
            'efficiency_penalty': -0.2  

        }
    
    def calculate_priority_scores(self, 
                                 points: List[MaintenancePoint],
                                 reference_date: Optional[datetime] = None) -> List[PriorityScore]:
        
        if not reference_date:
            reference_date = datetime.now()
        
        scores = []
        
        clusters = self._create_proximity_clusters(points)
        
        for point in points:
            factors = {}
            score = 0
            
            priority_value = point.priority.value
            factors['priority_base'] = priority_value * self.weights['priority_base']
            score += factors['priority_base']
            
           
            if point.complaints_count > 0:
                factors['complaints'] = point.complaints_count * self.weights['complaints']
                score += factors['complaints']
            
            if point.near_critical:
                factors['critical_location'] = self.weights['critical_location']
                score += factors['critical_location']
            
            if point.main_road:
                factors['main_road'] = self.weights['main_road']
                score += factors['main_road']
            
            if point.affects_traffic:
                factors['traffic_impact'] = self.weights['traffic_impact']
                score += factors['traffic_impact']
            
            if point.affects_commerce:
                factors['commerce_impact'] = self.weights['commerce_impact']
                score += factors['commerce_impact']
            
            days_waiting = (reference_date - point.created_at).days
            if days_waiting > 0:
                factors['time_waiting'] = days_waiting * self.weights['time_waiting']
                score += factors['time_waiting']
            
            cluster_size = len(clusters.get(point.id, []))
            if cluster_size > 1:
                factors['cluster_bonus'] = (cluster_size - 1) * self.weights['cluster_bonus']
                score += factors['cluster_bonus']
            
            if point.estimated_time > 120:
                penalty = (point.estimated_time - 120) * self.weights['efficiency_penalty']
                factors['efficiency_penalty'] = penalty
                score += penalty
            
            scores.append(PriorityScore(point, score, factors))
        
        return sorted(scores)
    
    def _create_proximity_clusters(self, points: List[MaintenancePoint], 
                                  radius_km: float = 0.5) -> Dict[str, List[MaintenancePoint]]:
       
        from src.core.algorithms.distance import haversine_distance
        
        clusters = defaultdict(list)
        
        for i, point1 in enumerate(points):
            for j, point2 in enumerate(points[i+1:], i+1):
                distance = haversine_distance(point1.coordinates, point2.coordinates)
                if distance <= radius_km:
                    clusters[point1.id].append(point2)
                    clusters[point2.id].append(point1)
        
        return clusters
    
    def optimize_team_schedule(self, 
                              points: List[MaintenancePoint],
                              teams: Dict[TeamType, int],
                              work_hours: int = 8) -> Dict[TeamType, List[List[MaintenancePoint]]]:
       
        scored_points = self.calculate_priority_scores(points)
        
        points_by_team = defaultdict(list)
        for score_obj in scored_points:
            points_by_team[score_obj.point.team_type].append(score_obj)
        
        schedule = {}
        
        for team_type, num_teams in teams.items():
            if team_type not in points_by_team:
                continue
            
            team_points = points_by_team[team_type]
            team_schedules = [[] for _ in range(num_teams)]
            team_times = [0] * num_teams
            max_time = work_hours * 60  
            
            heap = [(0, i) for i in range(num_teams)]
            heapq.heapify(heap)
            
            for score_obj in team_points:
                point = score_obj.point
                
                current_time, team_idx = heapq.heappop(heap)
                
                if current_time + point.estimated_time <= max_time:
                    team_schedules[team_idx].append(point)
                    new_time = current_time + point.estimated_time + 10  
                    heapq.heappush(heap, (new_time, team_idx))
            
            schedule[team_type] = team_schedules
        
        return schedule
    
    def suggest_next_points(self, 
                           current_point: MaintenancePoint,
                           available_points: List[MaintenancePoint],
                           max_suggestions: int = 5) -> List[Tuple[MaintenancePoint, float]]:
        
        from src.core.algorithms.distance import haversine_distance
        
        suggestions = []
        
        for point in available_points:
            if point.id == current_point.id:
                continue
            
            score = 0
            
            distance = haversine_distance(current_point.coordinates, point.coordinates)
            distance_score = 100 / (1 + distance)  
            score += distance_score * 0.4
            
            priority_score = point.priority.value * 20
            score += priority_score * 0.3
            
            if point.team_type == current_point.team_type:
                score += 30
            
            common_materials = set(current_point.materials) & set(point.materials)
            if common_materials:
                score += len(common_materials) * 5
            
            if point.neighborhood == current_point.neighborhood:
                score += 20
            
            suggestions.append((point, score))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:max_suggestions]
    
    def calculate_route_efficiency(self, route: List[MaintenancePoint]) -> Dict[str, float]:
       
        if not route:
            return {}
        
        from src.core.algorithms.distance import haversine_distance
        
        metrics = {
            'total_points': len(route),
            'total_time_minutes': sum(p.estimated_time for p in route),
            'total_complaints_resolved': sum(p.complaints_count for p in route),
            'emergency_ratio': len([p for p in route if p.priority == Priority.EMERGENCIA]) / len(route),
            'urgency_weighted_score': sum(p.priority.value for p in route) / len(route),
        }
        
        total_distance = 0
        for i in range(len(route) - 1):
            total_distance += haversine_distance(
                route[i].coordinates,
                route[i + 1].coordinates
            )
        metrics['total_distance_km'] = total_distance
        
        if total_distance > 0:
            metrics['efficiency_points_per_km'] = len(route) / total_distance
        else:
            metrics['efficiency_points_per_km'] = len(route)
        
        neighborhoods = set(p.neighborhood for p in route)
        metrics['neighborhood_coverage'] = len(neighborhoods)
        
        metrics['avg_time_per_point'] = metrics['total_time_minutes'] / len(route)
        
        efficiency_score = 0
        efficiency_score += min(metrics['emergency_ratio'] * 50, 30) 
        efficiency_score += min(metrics['efficiency_points_per_km'] * 5, 25)  
        efficiency_score += min(metrics['neighborhood_coverage'] * 3, 25)  
        efficiency_score += max(0, 20 - metrics['avg_time_per_point'] / 3) 
        
        metrics['overall_efficiency_score'] = min(efficiency_score, 100)
        
        return metrics

class BatchPrioritizer:
    
    @staticmethod
    def create_work_batches(points: List[MaintenancePoint],
                          batch_size: int = 10,
                          strategy: str = 'priority') -> List[List[MaintenancePoint]]:
     
        batches = []
        
        if strategy == 'priority':
            priority_groups = defaultdict(list)
            for point in points:
                priority_groups[point.priority].append(point)
            
            for priority in [Priority.EMERGENCIA, Priority.URGENTE, 
                           Priority.ALTA, Priority.MEDIA, Priority.BAIXA]:
                if priority in priority_groups:
                    group = priority_groups[priority]
                    for i in range(0, len(group), batch_size):
                        batch = group[i:i + batch_size]
                        if batch:
                            batches.append(batch)
        
        elif strategy == 'geographic':
            from sklearn.cluster import KMeans
            import numpy as np
            
            if len(points) <= batch_size:
                return [points]
            
            coords = np.array([p.coordinates for p in points])
            n_clusters = max(1, len(points) // batch_size)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(coords)
            
            clusters = defaultdict(list)
            for point, label in zip(points, labels):
                clusters[label].append(point)
            
            batches = list(clusters.values())
        
        elif strategy == 'mixed':
            emergencies = [p for p in points if p.priority == Priority.EMERGENCIA]
            others = [p for p in points if p.priority != Priority.EMERGENCIA]
            
            if emergencies:
                batches.append(emergencies)
            
            if others:
                geo_batches = BatchPrioritizer.create_work_batches(
                    others, batch_size, 'geographic'
                )
                batches.extend(geo_batches)
        
        return batches