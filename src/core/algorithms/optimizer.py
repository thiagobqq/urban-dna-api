import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import networkx as nx
from sklearn.cluster import DBSCAN
from concurrent.futures import ThreadPoolExecutor
import math

from src.core.models.point import MaintenancePoint, Priority, TeamType
from src.core.algorithms.distance import haversine_distance

@dataclass
class RouteResult:
    """Resultado da otimização de rota."""
    route: List[MaintenancePoint]
    total_distance: float
    total_time: int
    team_type: TeamType
    statistics: Dict

class TagBasedOptimizer:
    def __init__(self, points: List[MaintenancePoint]):
        self.points = points
        self.distance_cache = {}
        
    def optimize_route(self, 
                      team_type: TeamType,
                      max_hours: int = 8,
                      start_point: Optional[MaintenancePoint] = None) -> RouteResult:
       
        team_points = [p for p in self.points if p.team_type == team_type]
        
        if not team_points:
            return RouteResult([], 0, 0, team_type, {})
        
        priority_groups = self._group_by_priority(team_points)
        clusters = self._create_geographical_clusters(team_points)
        
        selected_points = self._select_points_by_priority(
            priority_groups, 
            max_hours * 60
        )
        
        cluster_routes = self._optimize_clusters(selected_points, clusters)
        
        final_route = self._connect_clusters(cluster_routes, start_point)
        
        final_route = self._two_opt_improvement(final_route)
        
        total_distance = self._calculate_total_distance(final_route)
        total_time = sum(p.estimated_time for p in final_route)
        stats = self._generate_statistics(final_route)
        
        return RouteResult(
            route=final_route,
            total_distance=total_distance,
            total_time=total_time,
            team_type=team_type,
            statistics=stats
        )
    
    def _group_by_priority(self, points: List[MaintenancePoint]) -> Dict:
      
        groups = {}
        for point in points:
            if point.priority not in groups:
                groups[point.priority] = []
            groups[point.priority].append(point)
        return groups
    
    def _create_geographical_clusters(self, points: List[MaintenancePoint]) -> Dict:
      
        if len(points) < 2:
            return {0: points}
        
        coords = np.array([p.coordinates for p in points])
        
        clustering = DBSCAN(eps=0.01, min_samples=2, metric='haversine')
        clustering.fit(np.radians(coords))
        
        clusters = {}
        for i, label in enumerate(clustering.labels_):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(points[i])
        
        return clusters
    
    def _select_points_by_priority(self, 
                                  priority_groups: Dict,
                                  max_minutes: int) -> List[MaintenancePoint]:
       
        selected = []
        time_used = 0
        
        priority_order = [
            Priority.EMERGENCIA,
            Priority.URGENTE,
            Priority.ALTA,
            Priority.MEDIA,
            Priority.BAIXA
        ]
        
        for priority in priority_order:
            if priority not in priority_groups:
                continue
                
            points = priority_groups[priority]
            
            points.sort(key=lambda p: p.urgency_score, reverse=True)
            
            for point in points:
                time_needed = point.estimated_time + 10
                
                if time_used + time_needed <= max_minutes:
                    selected.append(point)
                    time_used += time_needed
                else:
                    break
            
            if time_used >= max_minutes:
                break
        
        return selected
    
    def _optimize_clusters(self, 
                          points: List[MaintenancePoint],
                          clusters: Dict) -> List[List[MaintenancePoint]]:
        
        cluster_routes = []
        
        point_to_cluster = {}
        for cluster_id, cluster_points in clusters.items():
            for p in cluster_points:
                point_to_cluster[p.id] = cluster_id
        
        selected_clusters = {}
        for point in points:
            cluster_id = point_to_cluster.get(point.id, -1)
            if cluster_id not in selected_clusters:
                selected_clusters[cluster_id] = []
            selected_clusters[cluster_id].append(point)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for cluster_points in selected_clusters.values():
                future = executor.submit(self._nearest_neighbor, cluster_points)
                futures.append(future)
            
            for future in futures:
                cluster_routes.append(future.result())
        
        return cluster_routes
    
    def _nearest_neighbor(self, points: List[MaintenancePoint]) -> List[MaintenancePoint]:
        if len(points) <= 1:
            return points
        
        route = [points[0]]
        unvisited = set(points[1:])
        
        while unvisited:
            current = route[-1]
            nearest = min(
                unvisited,
                key=lambda p: self._get_distance(current, p)
            )
            route.append(nearest)
            unvisited.remove(nearest)
        
        return route
    
    def _connect_clusters(self, 
                         cluster_routes: List[List[MaintenancePoint]],
                         start_point: Optional[MaintenancePoint]) -> List[MaintenancePoint]:
      
        if not cluster_routes:
            return []
        
        if len(cluster_routes) == 1:
            return cluster_routes[0]
        
        G = nx.Graph()
        
        for i, route in enumerate(cluster_routes):
                centroid = self._calculate_centroid(route)
                G.add_node(i, centroid=centroid, route=route)
        
        nodes = list(G.nodes())
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                centroid_i = G.nodes[nodes[i]]['centroid']
                centroid_j = G.nodes[nodes[j]]['centroid']
                distance = haversine_distance(centroid_i, centroid_j)
                G.add_edge(nodes[i], nodes[j], weight=distance)
        
        if len(nodes) > 1:
            mst = nx.minimum_spanning_tree(G)
            
            start_node = 0
            if start_point:
                min_dist = float('inf')
                for node in nodes:
                    centroid = G.nodes[node]['centroid']
                    dist = haversine_distance(start_point.coordinates, centroid)
                    if dist < min_dist:
                        min_dist = dist
                        start_node = node
            
            visit_order = list(nx.dfs_preorder_nodes(mst, start_node))
        else:
            visit_order = nodes
        
        final_route = []
        for node in visit_order:
            final_route.extend(G.nodes[node]['route'])
        
        return final_route
    
    def _two_opt_improvement(self, route: List[MaintenancePoint]) -> List[MaintenancePoint]:
  
        if len(route) < 4:
            return route
        
        improved = True
        current_route = route.copy()
        
        while improved:
            improved = False
            for i in range(1, len(current_route) - 2):
                for j in range(i + 1, len(current_route)):
                    if j - i == 1:
                        continue
                    
                    old_distance = (
                        self._get_distance(current_route[i-1], current_route[i]) +
                        self._get_distance(current_route[j-1], current_route[j % len(current_route)])
                    )
                    
                    new_distance = (
                        self._get_distance(current_route[i-1], current_route[j-1]) +
                        self._get_distance(current_route[i], current_route[j % len(current_route)])
                    )
                    
                    if new_distance < old_distance:
                        current_route[i:j] = reversed(current_route[i:j])
                        improved = True
        
        return current_route
    
    def _get_distance(self, p1: MaintenancePoint, p2: MaintenancePoint) -> float:
        cache_key = (p1.id, p2.id)
        if cache_key not in self.distance_cache:
            self.distance_cache[cache_key] = haversine_distance(
                p1.coordinates, 
                p2.coordinates
            )
        return self.distance_cache[cache_key]
    
    def _calculate_centroid(self, points: List[MaintenancePoint]) -> Tuple[float, float]:
        if not points:
            return (0, 0)
        
        lat_mean = sum(p.latitude for p in points) / len(points)
        lon_mean = sum(p.longitude for p in points) / len(points)
        
        return (lat_mean, lon_mean)
    
    def _calculate_total_distance(self, route: List[MaintenancePoint]) -> float:
      
        if len(route) < 2:
            return 0
        
        total = 0
        for i in range(len(route) - 1):
            total += self._get_distance(route[i], route[i + 1])
        
        total += self._get_distance(route[-1], route[0])
        
        return total
    
    def _generate_statistics(self, route: List[MaintenancePoint]) -> Dict:
      
        if not route:
            return {}
        
        return {
            "total_points": len(route),
            "emergencies": len([p for p in route if p.priority == Priority.EMERGENCIA]),
            "urgent": len([p for p in route if p.priority == Priority.URGENTE]),
            "complaints_resolved": sum(p.complaints_count for p in route),
            "main_roads": len([p for p in route if p.main_road]),
            "critical_locations": len([p for p in route if p.near_critical]),
            "neighborhoods": len(set(p.neighborhood for p in route)),
            "road_blocks_needed": len([p for p in route if p.requires_road_block])
        }