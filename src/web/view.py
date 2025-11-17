import folium
from folium.plugins import MarkerCluster, HeatMap, AntPath
import json
from typing import List, Dict, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import base64
from io import BytesIO

from src.core.models.point import MaintenancePoint, Priority, TeamType

class RouteVisualizer:
    """Cria visualizações de rotas otimizadas."""
    
    def __init__(self):
        self.color_map = {
            Priority.EMERGENCIA: 'red',
            Priority.URGENTE: 'orange',
            Priority.ALTA: 'yellow',
            Priority.MEDIA: 'blue',
            Priority.BAIXA: 'green'
        }
        
        self.team_colors = {
            TeamType.ASFALTO: '#8B4513',  # brown
            TeamType.HIDRAULICA: '#4169E1',  # blue
            TeamType.ELETRICA: '#FFD700',  # gold
            TeamType.SANEAMENTO: '#228B22',  # green
            TeamType.GERAL: '#808080'  # gray
        }
    
    def create_route_map(self, 
                        points: List[MaintenancePoint],
                        route: List[MaintenancePoint],
                        save_path: str = "route_map.html") -> folium.Map:
        """
        Cria mapa interativo com a rota otimizada.
        """
        # Calcular centro do mapa
        if route:
            lat_center = sum(p.latitude for p in route) / len(route)
            lon_center = sum(p.longitude for p in route) / len(route)
        else:
            lat_center = sum(p.latitude for p in points) / len(points)
            lon_center = sum(p.longitude for p in points) / len(points)
        
        # Criar mapa base
        m = folium.Map(
            location=[lat_center, lon_center],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        # Adicionar camadas de tiles alternativas
        folium.TileLayer('CartoDB positron').add_to(m)
        folium.TileLayer('CartoDB dark_matter').add_to(m)
        
        # Criar clusters de marcadores
        marker_cluster = MarkerCluster().add_to(m)
        
        # Adicionar todos os pontos
        for point in points:
            color = self.color_map.get(point.priority, 'gray')
            icon = self._get_icon_for_problem(point.problem_type)
            
            # Criar popup HTML detalhado
            popup_html = f"""
            <div style="width: 250px;">
                <h4>{point.address}</h4>
                <table style="width: 100%;">
                    <tr><td><b>ID:</b></td><td>{point.id}</td></tr>
                    <tr><td><b>Problema:</b></td><td>{point.problem_type.value}</td></tr>
                    <tr><td><b>Prioridade:</b></td><td>{point.priority.name}</td></tr>
                    <tr><td><b>Equipe:</b></td><td>{point.team_type.value}</td></tr>
                    <tr><td><b>Tempo Est.:</b></td><td>{point.estimated_time} min</td></tr>
                    <tr><td><b>Reclamações:</b></td><td>{point.complaints_count}</td></tr>
                    <tr><td><b>Bairro:</b></td><td>{point.neighborhood}</td></tr>
                </table>
                {self._create_impact_badges(point)}
            </div>
            """
            
            folium.Marker(
                location=[point.latitude, point.longitude],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon=icon, prefix='fa'),
                tooltip=f"{point.problem_type.value} - {point.priority.name}"
            ).add_to(marker_cluster)
        
        # Adicionar rota otimizada se existir
        if route and len(route) > 1:
            # Criar linha da rota
            route_coords = [[p.latitude, p.longitude] for p in route]
            
            # Linha animada (ant path)
            AntPath(
                locations=route_coords,
                color='red',
                weight=4,
                opacity=0.8,
                delay=1000,
                dash_array=[10, 20],
                pulse_color='darkred'
            ).add_to(m)
            
            # Adicionar números de ordem
            for i, point in enumerate(route, 1):
                folium.Marker(
                    location=[point.latitude, point.longitude],
                    icon=folium.DivIcon(
                        html=f"""
                        <div style="
                            background-color: white;
                            border: 2px solid red;
                            border-radius: 50%;
                            width: 30px;
                            height: 30px;
                            text-align: center;
                            line-height: 30px;
                            font-weight: bold;
                            font-size: 14px;
                        ">{i}</div>
                        """
                    )
                ).add_to(m)
        
        # Adicionar heatmap de problemas
        if len(points) > 10:
            heat_data = [[p.latitude, p.longitude, p.priority.value] for p in points]
            HeatMap(heat_data, radius=15, blur=10).add_to(m)
        
        # Adicionar controle de camadas
        folium.LayerControl().add_to(m)
        
        # Adicionar legenda
        self._add_legend(m)
        
        # Salvar mapa
        m.save(save_path)
        print(f"Mapa salvo em: {save_path}")
        
        return m
    
    def _get_icon_for_problem(self, problem_type) -> str:
        """Retorna ícone apropriado para cada tipo de problema."""
        icon_map = {
            'buraco_asfalto': 'road',
            'vazamento_agua': 'tint',
            'vazamento_esgoto': 'exclamation-triangle',
            'poste_sem_luz': 'lightbulb',
            'fiacao_exposta': 'bolt',
            'bueiro_entupido': 'circle',
            'calcada_quebrada': 'walking',
            'semaforo_defeito': 'traffic-light'
        }
        return icon_map.get(problem_type.value, 'wrench')
    
    def _create_impact_badges(self, point: MaintenancePoint) -> str:
        """Cria badges HTML para mostrar impactos."""
        badges = []
        
        if point.affects_traffic:
            badges.append('<span style="background: #ff6b6b; color: white; padding: 2px 5px; border-radius: 3px; margin: 2px;">Afeta Trânsito</span>')
        
        if point.affects_commerce:
            badges.append('<span style="background: #4ecdc4; color: white; padding: 2px 5px; border-radius: 3px; margin: 2px;">Afeta Comércio</span>')
        
        if point.near_critical:
            badges.append('<span style="background: #f7b731; color: white; padding: 2px 5px; border-radius: 3px; margin: 2px;">Local Crítico</span>')
        
        if point.main_road:
            badges.append('<span style="background: #5f27cd; color: white; padding: 2px 5px; border-radius: 3px; margin: 2px;">Via Principal</span>')
        
        return '<div style="margin-top: 10px;">' + ' '.join(badges) + '</div>' if badges else ''
    
    def _add_legend(self, m: folium.Map):
        """Adiciona legenda ao mapa."""
        legend_html = '''
        <div style="
            position: fixed;
            bottom: 50px;
            left: 50px;
            width: 200px;
            background-color: white;
            border: 2px solid grey;
            border-radius: 5px;
            z-index: 9999;
            font-size: 14px;
            padding: 10px;
        ">
            <p style="margin: 0; font-weight: bold;">Legenda de Prioridades</p>
            <p style="margin: 5px 0;"><span style="color: red;">●</span> Emergência</p>
            <p style="margin: 5px 0;"><span style="color: orange;">●</span> Urgente</p>
            <p style="margin: 5px 0;"><span style="color: yellow;">●</span> Alta</p>
            <p style="margin: 5px 0;"><span style="color: blue;">●</span> Média</p>
            <p style="margin: 5px 0;"><span style="color: green;">●</span> Baixa</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def create_statistics_dashboard(self, 
                                   route: List[MaintenancePoint],
                                   statistics: Dict,
                                   save_path: str = "dashboard.png"):
        """
        Cria dashboard com estatísticas da otimização.
        """
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Dashboard de Otimização de Rotas', fontsize=16)
        
        # 1. Distribuição por Prioridade
        priority_counts = {}
        for p in route:
            priority_counts[p.priority.name] = priority_counts.get(p.priority.name, 0) + 1
        
        axes[0, 0].pie(priority_counts.values(), labels=priority_counts.keys(), autopct='%1.1f%%')
        axes[0, 0].set_title('Distribuição por Prioridade')
        
        # 2. Tempo por Bairro
        time_by_neighborhood = {}
        for p in route:
            time_by_neighborhood[p.neighborhood] = time_by_neighborhood.get(p.neighborhood, 0) + p.estimated_time
        
        axes[0, 1].bar(time_by_neighborhood.keys(), time_by_neighborhood.values())
        axes[0, 1].set_title('Tempo Total por Bairro (min)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Linha do tempo de execução
        times = [0]
        accumulated_time = 0
        for p in route:
            accumulated_time += p.estimated_time
            times.append(accumulated_time)
        
        axes[0, 2].plot(range(len(times)), times, marker='o')
        axes[0, 2].set_title('Tempo Acumulado')
        axes[0, 2].set_xlabel('Número de Pontos')
        axes[0, 2].set_ylabel('Tempo (min)')
        
        # 4. Impactos
        impacts = {
            'Afeta Trânsito': len([p for p in route if p.affects_traffic]),
            'Afeta Comércio': len([p for p in route if p.affects_commerce]),
            'Local Crítico': len([p for p in route if p.near_critical]),
            'Via Principal': len([p for p in route if p.main_road])
        }
        
        axes[1, 0].barh(list(impacts.keys()), list(impacts.values()))
        axes[1, 0].set_title('Impactos Atendidos')
        axes[1, 0].set_xlabel('Quantidade')
        
        # 5. Métricas de Eficiência
        metrics_data = {
            'Pontos': statistics.get('total_points', 0),
            'Emergências': statistics.get('emergencies', 0),
            'Reclamações': statistics.get('complaints_resolved', 0) // 10,  # Dividir para caber no gráfico
            'Bairros': statistics.get('neighborhoods', 0)
        }
        
        axes[1, 1].bar(metrics_data.keys(), metrics_data.values(), color=['blue', 'red', 'green', 'orange'])
        axes[1, 1].set_title('Métricas Gerais')
        
        # 6. Distribuição de Tempo de Trabalho
        time_distribution = [p.estimated_time for p in route]
        axes[1, 2].hist(time_distribution, bins=10, edgecolor='black')
        axes[1, 2].set_title('Distribuição de Tempo por Trabalho')
        axes[1, 2].set_xlabel('Tempo (min)')
        axes[1, 2].set_ylabel('Frequência')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Dashboard salvo em: {save_path}")
    
    def create_comparison_chart(self,
                              routes: Dict[str, List[MaintenancePoint]],
                              save_path: str = "comparison.png"):
        """
        Cria gráfico comparando múltiplas rotas/equipes.
        """
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Preparar dados
        teams = list(routes.keys())
        points_count = [len(route) for route in routes.values()]
        total_time = [sum(p.estimated_time for p in route) for route in routes.values()]
        emergencies = [len([p for p in route if p.priority == Priority.EMERGENCIA]) 
                      for route in routes.values()]
        
        # Gráfico 1: Comparação de cargas
        x = range(len(teams))
        width = 0.25
        
        axes[0].bar([i - width for i in x], points_count, width, label='Pontos', color='blue')
        axes[0].bar(x, [t/10 for t in total_time], width, label='Tempo/10 (min)', color='green')
        axes[0].bar([i + width for i in x], emergencies, width, label='Emergências', color='red')
        
        axes[0].set_xlabel('Equipes')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(teams)
        axes[0].set_ylabel('Quantidade')
        axes[0].set_title('Comparação de Carga por Equipe')
        axes[0].legend()
        
        # Gráfico 2: Eficiência
        efficiency = [p/t * 60 if t > 0 else 0 for p, t in zip(points_count, total_time)]
        
        axes[1].barh(teams, efficiency, color='purple')
        axes[1].set_xlabel('Pontos por Hora')
        axes[1].set_title('Eficiência por Equipe')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Gráfico de comparação salvo em: {save_path}")

def generate_html_report(route: List[MaintenancePoint],
                        statistics: Dict,
                        map_path: str,
                        dashboard_path: str) -> str:
    """
    Gera relatório HTML completo da otimização.
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório de Otimização de Rotas</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .stat-label {{
                color: #7f8c8d;
                margin-top: 5px;
            }}
            .route-table {{
                width: 100%;
                background: white;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .route-table th, .route-table td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            .route-table th {{
                background-color: #34495e;
                color: white;
            }}
            .priority-emergencia {{ color: #e74c3c; font-weight: bold; }}
            .priority-urgente {{ color: #e67e22; font-weight: bold; }}
            .priority-alta {{ color: #f39c12; }}
            .priority-media {{ color: #3498db; }}
            .priority-baixa {{ color: #27ae60; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório de Otimização de Rotas</h1>
            <p>Gerado em: {timestamp}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_points}</div>
                <div class="stat-label">Pontos Atendidos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_distance:.1f} km</div>
                <div class="stat-label">Distância Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_time} min</div>
                <div class="stat-label">Tempo Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{emergencies}</div>
                <div class="stat-label">Emergências</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{complaints}</div>
                <div class="stat-label">Reclamações Resolvidas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{neighborhoods}</div>
                <div class="stat-label">Bairros Atendidos</div>
            </div>
        </div>
        
        <h2>Rota Otimizada</h2>
        <table class="route-table">
            <thead>
                <tr>
                    <th>Ordem</th>
                    <th>Endereço</th>
                    <th>Problema</th>
                    <th>Prioridade</th>
                    <th>Tempo (min)</th>
                    <th>Bairro</th>
                </tr>
            </thead>
            <tbody>
                {route_rows}
            </tbody>
        </table>
        
        <h2>Visualizações</h2>
        <iframe src="{map_path}" width="100%" height="600" frameborder="0"></iframe>
        
        <img src="{dashboard_path}" alt="Dashboard" style="width: 100%; margin-top: 20px;">
    </body>
    </html>
    """
    
    # Preparar dados
    route_rows = ""
    for i, point in enumerate(route, 1):
        route_rows += f"""
        <tr>
            <td>{i}</td>
            <td>{point.address}</td>
            <td>{point.problem_type.value}</td>
            <td class="priority-{point.priority.name.lower()}">{point.priority.name}</td>
            <td>{point.estimated_time}</td>
            <td>{point.neighborhood}</td>
        </tr>
        """
    
    # Preencher template
    html = html_template.format(
        timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"),
        total_points=len(route),
        total_distance=statistics.get('total_distance_km', 0),
        total_time=sum(p.estimated_time for p in route),
        emergencies=statistics.get('emergencies', 0),
        complaints=statistics.get('complaints_resolved', 0),
        neighborhoods=statistics.get('neighborhoods', 0),
        route_rows=route_rows,
        map_path=map_path,
        dashboard_path=dashboard_path
    )
    
    # Salvar HTML
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("Relatório HTML gerado: report.html")
    
    return html