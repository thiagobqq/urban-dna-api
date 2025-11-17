import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from src.core.models.point import MaintenancePoint, Priority, ProblemType, TeamType
from src.core.algorithms.optimizer import TagBasedOptimizer
from src.core.algorithms.prioritizer import IntelligentPrioritizer
from src.core.algorithms.distance import haversine_distance

class TestOptimizer:
    """Testes para o otimizador de rotas."""
    
    @pytest.fixture
    def sample_points(self) -> List[MaintenancePoint]:
        """Cria pontos de teste."""
        return [
            MaintenancePoint(
                id="1",
                latitude=-10.965490,
                longitude=-37.057259,
                address="Rua A, 123",
                problem_type=ProblemType.BURACO_ASFALTO,
                priority=Priority.EMERGENCIA,
                team_type=TeamType.ASFALTO,
                problem_size="grande",
                estimated_time=45,
                neighborhood="Centro",
                region="Centro",
                main_road=True,
                complaints_count=15,
                affects_traffic=True,
                created_at=datetime.now() - timedelta(days=3)
            ),
            MaintenancePoint(
                id="2",
                latitude=-10.967000,
                longitude=-37.058000,
                address="Rua B, 456",
                problem_type=ProblemType.VAZAMENTO_AGUA,
                priority=Priority.URGENTE,
                team_type=TeamType.HIDRAULICA,
                problem_size="medio",
                estimated_time=60,
                neighborhood="Centro",
                region="Centro",
                complaints_count=8,
                near_critical=True,
                created_at=datetime.now() - timedelta(days=2)
            ),
            MaintenancePoint(
                id="3",
                latitude=-10.970000,
                longitude=-37.060000,
                address="Rua C, 789",
                problem_type=ProblemType.BURACO_ASFALTO,
                priority=Priority.ALTA,
                team_type=TeamType.ASFALTO,
                problem_size="pequeno",
                estimated_time=20,
                neighborhood="Centro",
                region="Centro",
                complaints_count=3,
                created_at=datetime.now() - timedelta(days=5)
            ),
            MaintenancePoint(
                id="4",
                latitude=-10.960000,
                longitude=-37.055000,
                address="Av. D, 321",
                problem_type=ProblemType.POSTE_SEM_LUZ,
                priority=Priority.MEDIA,
                team_type=TeamType.ELETRICA,
                problem_size="medio",
                estimated_time=30,
                neighborhood="Sul",
                region="Sul",
                complaints_count=5,
                created_at=datetime.now() - timedelta(days=1)
            ),
            MaintenancePoint(
                id="5",
                latitude=-10.962000,
                longitude=-37.056000,
                address="Rua E, 654",
                problem_type=ProblemType.BURACO_ASFALTO,
                priority=Priority.BAIXA,
                team_type=TeamType.ASFALTO,
                problem_size="pequeno",
                estimated_time=15,
                neighborhood="Sul",
                region="Sul",
                complaints_count=1,
                created_at=datetime.now() - timedelta(days=7)
            )
        ]
    
    def test_optimizer_initialization(self, sample_points):
        """Testa inicialização do otimizador."""
        optimizer = TagBasedOptimizer(sample_points)
        assert optimizer.points == sample_points
        assert len(optimizer.distance_cache) == 0
    
    def test_optimize_route_asfalto(self, sample_points):
        """Testa otimização para equipe de asfalto."""
        optimizer = TagBasedOptimizer(sample_points)
        result = optimizer.optimize_route(TeamType.ASFALTO, max_hours=8)
        
        assert result.team_type == TeamType.ASFALTO
        assert len(result.route) > 0
        assert all(p.team_type == TeamType.ASFALTO for p in result.route)
        assert result.total_time <= 8 * 60  # Não excede 8 horas
    
    def test_priority_ordering(self, sample_points):
        """Verifica se emergências vêm primeiro."""
        optimizer = TagBasedOptimizer(sample_points)
        result = optimizer.optimize_route(TeamType.ASFALTO, max_hours=8)
        
        # Emergências devem vir antes de não-emergências
        emergency_found = False
        non_emergency_after = False
        
        for point in result.route:
            if point.priority == Priority.EMERGENCIA:
                emergency_found = True
            elif emergency_found and point.priority != Priority.EMERGENCIA:
                non_emergency_after = True
                break
        
        # Se houver emergência, não deve haver não-emergência antes dela
        if emergency_found:
            assert result.route[0].priority == Priority.EMERGENCIA
    
    def test_distance_calculation(self):
        """Testa cálculo de distância."""
        coord1 = (-10.965490, -37.057259)
        coord2 = (-10.967000, -37.058000)
        
        distance = haversine_distance(coord1, coord2)
        
        assert distance > 0
        assert distance < 1  # Menos de 1km entre esses pontos
    
    def test_clustering(self, sample_points):
        """Testa criação de clusters geográficos."""
        optimizer = TagBasedOptimizer(sample_points)
        clusters = optimizer._create_geographical_clusters(sample_points)
        
        assert len(clusters) > 0
        assert all(isinstance(points, list) for points in clusters.values())
    
    def test_prioritizer_scoring(self, sample_points):
        """Testa sistema de priorização."""
        prioritizer = IntelligentPrioritizer()
        scores = prioritizer.calculate_priority_scores(sample_points)
        
        assert len(scores) == len(sample_points)
        assert all(hasattr(s, 'score') for s in scores)
        
        # Emergências devem ter score mais alto
        emergency_scores = [s.score for s in scores if s.point.priority == Priority.EMERGENCIA]
        low_priority_scores = [s.score for s in scores if s.point.priority == Priority.BAIXA]
        
        if emergency_scores and low_priority_scores:
            assert max(low_priority_scores) < min(emergency_scores)
    
    def test_route_efficiency_metrics(self, sample_points):
        """Testa cálculo de métricas de eficiência."""
        prioritizer = IntelligentPrioritizer()
        optimizer = TagBasedOptimizer(sample_points)
        
        result = optimizer.optimize_route(TeamType.ASFALTO)
        metrics = prioritizer.calculate_route_efficiency(result.route)
        
        assert 'total_points' in metrics
        assert 'total_distance_km' in metrics
        assert 'overall_efficiency_score' in metrics
        assert 0 <= metrics['overall_efficiency_score'] <= 100
    
    def test_empty_points_handling(self):
        """Testa comportamento com lista vazia."""
        optimizer = TagBasedOptimizer([])
        result = optimizer.optimize_route(TeamType.ASFALTO)
        
        assert result.route == []
        assert result.total_distance == 0
        assert result.total_time == 0
    
    def test_single_point_handling(self, sample_points):
        """Testa com apenas um ponto."""
        single_point = [sample_points[0]]
        optimizer = TagBasedOptimizer(single_point)
        result = optimizer.optimize_route(TeamType.ASFALTO)
        
        assert len(result.route) == 1
        assert result.route[0] == single_point[0]
    
    @pytest.mark.asyncio
    async def test_database_operations(self):
        """Testa operações de banco de dados (requer banco configurado)."""
        from src.infra.database import get_database
        
        try:
            db = await get_database()
            stats = await db.get_statistics()
            assert isinstance(stats, dict)
        except Exception as e:
            pytest.skip(f"Banco de dados não disponível: {e}")

def test_suite():
    """Executa todos os testes."""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    test_suite()