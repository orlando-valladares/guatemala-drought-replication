#!/usr/bin/env python3
# Reproducible municipal aggregation of the immutable MAGA 2025 land-use SHP.
# The SHP's CODIGO field allows direct aggregation: no repeated spatial parsing.
from pathlib import Path
import re, shutil, unicodedata
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import make_valid

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(x for x in PROJECT.parents if x.name == '01_workspace')
GUATEMALA = WORKSPACE/'02_projects/07_Playdata/02_Guatemala'
SHP = GUATEMALA/'sources/MAGA_uso_de_tierra/SHP_cobertura_vegetal_y_uso_de_la_tierra_2025/SHP_cobertura_vegetal_y_uso_de_la_tierra_2025.shp'
MUNIS = GUATEMALA/'sources/JSON_Departamenos_Municipios_LugaresPoblados/Mapas-TopoJSON-Guatemala-main/munis.json'
CENSUS = GUATEMALA/'sources/INE_Rama_Economica_2018/censo2018_cuadro_A12_2_municipios.csv'
DERIVED=PROJECT/'derived'; PROJECT_OUTPUT=PROJECT/'output/maga_uso_tierra_2025_exploration'; BODY=PROJECT/'figures/.tex_body'; OVERLEAF=PROJECT/'overleaf/assets/figures'; APP=PROJECT/'figures/Appendix/tables'
COUNTRY_FIGURES=GUATEMALA/'figures'; OUTPUT=COUNTRY_FIGURES/'maga_land_use_exploration'; DEPARTMENT_EXPORTS=COUNTRY_FIGURES/'showing_departments'
GREEN=['#ffffe5','#d9f0a3','#addd8e','#78c679','#31a354','#006837']
OXFAM={'JALAPA':99.96,'CHIQUIMULA':97.55,'BAJA VERAPAZ':86.83,'QUICHE':53.52,'HUEHUETENANGO':40.85,'ALTA VERAPAZ':38.95}

def norm(v):
    x=''.join(c for c in unicodedata.normalize('NFD',str(v)) if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',x).strip().upper()

def geo():
    g=gpd.read_file(MUNIS)
    if g.crs is None: g=g.set_crs('EPSG:4326')
    g=g.loc[~g.id.astype(str).eq('0') & ~g.Departamento.map(norm).eq('BELICE')].copy()
    g.loc[~g.geometry.is_valid,'geometry']=g.loc[~g.geometry.is_valid,'geometry'].map(make_valid)
    g['codigo_municipio_4d']=pd.to_numeric(g.id,errors='raise').astype(int).astype(str).str.zfill(4)
    if len(g)!=340 or g.codigo_municipio_4d.nunique()!=340: raise ValueError('Expected 340 analytical municipalities')
    return g[['codigo_municipio_4d','Departamento','Municipio','geometry']]

def aggregate(g):
    u=gpd.read_file(SHP)
    req={'CODIGO','DEPTO','MUNICIPIO','USOT','Nivel_1','Area_Ha_Aj'}
    if req-set(u): raise ValueError('MAGA required fields unavailable')
    u=u.loc[pd.to_numeric(u.CODIGO,errors='coerce').fillna(-1).astype(int).ne(0)].copy()
    u['codigo_municipio_4d']=u.CODIGO.astype(int).astype(str).str.zfill(4); u['Area_Ha_Aj']=pd.to_numeric(u.Area_Ha_Aj,errors='raise')
    if u.codigo_municipio_4d.nunique()!=340 or (u.Area_Ha_Aj<0).any(): raise ValueError('Invalid land-use code/area')
    base=u.groupby('codigo_municipio_4d',as_index=False).agg(maga_department=('DEPTO','first'),maga_municipality=('MUNICIPIO','first'),mapped_area_ha=('Area_Ha_Aj','sum'))
    ag=u.loc[u.Nivel_1.eq('2. Territorios agrícolas')].groupby('codigo_municipio_4d',as_index=False).Area_Ha_Aj.sum().rename(columns={'Area_Ha_Aj':'agricultural_land_ha'})
    mb=u.loc[u.USOT.eq('Maíz y frijol')].groupby('codigo_municipio_4d',as_index=False).Area_Ha_Aj.sum().rename(columns={'Area_Ha_Aj':'maize_bean_ha'})
    m=g.drop(columns='geometry').merge(base,on='codigo_municipio_4d',validate='one_to_one').merge(ag,on='codigo_municipio_4d',how='left',validate='one_to_one').merge(mb,on='codigo_municipio_4d',how='left',validate='one_to_one')
    m[['agricultural_land_ha','maize_bean_ha']]=m[['agricultural_land_ha','maize_bean_ha']].fillna(0)
    c=pd.read_csv(CENSUS,dtype={'codigo_municipio_4d':str})
    m=m.merge(c[['codigo_municipio_4d','A','total']],on='codigo_municipio_4d',validate='one_to_one')
    m['agricultural_share_pct']=100*m.A/m.total
    m['agricultural_land_share_of_mapped_pct']=100*m.agricultural_land_ha/m.mapped_area_ha
    m['maize_bean_share_of_agricultural_land_pct']=100*m.maize_bean_ha/m.agricultural_land_ha
    m['ag_workers_per_100_agricultural_ha']=100*m.A/m.agricultural_land_ha
    if len(m)!=340 or m[['ag_workers_per_100_agricultural_ha','maize_bean_share_of_agricultural_land_pct']].isna().any().any(): raise ValueError('Mapped-land denominator unavailable')
    return m

def handles(labels):
    return [Patch(facecolor=c,edgecolor='#111111',linewidth=.45,label=l) for l,c in zip(labels,GREEN,strict=True)]+[Line2D([0],[0],marker='*',color='white',markerfacecolor='#111111',markeredgecolor='white',markersize=7.8,label='Ciudad de Guatemala')]

def draw(ax,g,var,bins,labels,title,head=11,department_borders=False):
    g=g.assign(_class=pd.cut(g[var],bins=bins,labels=labels,include_lowest=True,ordered=True))
    for label,color in zip(labels,GREEN,strict=True): g.loc[g._class.eq(label)].plot(ax=ax,color=color,edgecolor='#111111',linewidth=.16,zorder=1)
    if department_borders:
        g.dissolve(by='Departamento').boundary.plot(ax=ax,color='#111111',linewidth=.68,zorder=7)
    cap=g.loc[g.codigo_municipio_4d.eq('0101')].to_crs('EPSG:6933').copy(); cap['geometry']=cap.centroid
    cap.to_crs(g.crs).plot(ax=ax,marker='*',color='#111111',edgecolor='white',linewidth=.65,markersize=55,zorder=8)
    ax.text(0,1.012,title,transform=ax.transAxes,fontsize=head,fontweight='bold',va='bottom',linespacing=1.13); ax.set_axis_off(); ax.set_aspect('equal')

def save(fig,pdf,png=None,copy=False):
    pdf.parent.mkdir(parents=True,exist_ok=True); fig.savefig(pdf,bbox_inches='tight',pad_inches=.02,facecolor='white')
    if png: png.parent.mkdir(parents=True,exist_ok=True); fig.savefig(png,bbox_inches='tight',dpi=350,facecolor='white')
    if copy: OVERLEAF.mkdir(parents=True,exist_ok=True); shutil.copy2(pdf,OVERLEAF/pdf.name)
    plt.close(fig)

def main_map(g,var,bins,labels,title,legend,stem,*,department_borders=False,destination=None):
    fig,ax=plt.subplots(figsize=(6.1,6.35),facecolor='white'); draw(ax,g,var,bins,labels,title,department_borders=department_borders)
    leg=ax.legend(handles=handles(labels),title=legend,loc='lower left',fontsize=9.65,title_fontsize=9.65,frameon=False,ncol=3,columnspacing=.7,labelspacing=.35,handlelength=1.05); leg._legend_box.align='left'
    fig.subplots_adjust(left=.025,right=.975,top=.91,bottom=.025)
    if destination is None:
        save(fig,BODY/(stem+'_body.pdf'),PROJECT/'figures'/(stem+'.png'),True)
    else:
        save(fig,destination)

def department(m):
    d=m.assign(key=m.Departamento.map(norm)).groupby(['key','Departamento'],as_index=False).agg(agricultural_land_ha=('agricultural_land_ha','sum'),maize_bean_ha=('maize_bean_ha','sum'),agricultural_workers=('A','sum'),total_workers=('total','sum'))
    d['ag_workers_per_100_agricultural_ha']=100*d.agricultural_workers/d.agricultural_land_ha; d['agricultural_share_pct']=100*d.agricultural_workers/d.total_workers
    s=pd.read_csv(APP/'chirps_shock_comparison_department_common_reference.csv'); s['key']=s.department.map(norm)
    d=d.merge(s[['key','rain_2026_mm','hist_mean_mm','hist_median_mm','hist_sd_mm','z_2015_common','z_2026_common']],on='key',validate='one_to_one')
    d['drought_severity_negative_z']=np.maximum(-d.z_2026_common,0)
    d['drought_severity_negative_z_2015']=np.maximum(-d.z_2015_common,0)
    d['impact_composite']=d.ag_workers_per_100_agricultural_ha*d.drought_severity_negative_z
    d['impact_composite_2015']=d.ag_workers_per_100_agricultural_ha*d.drought_severity_negative_z_2015
    d['oxfam_households_with_losses_pct']=d.key.map(OXFAM)
    return d.sort_values(['impact_composite','Departamento'],ascending=[False,True]).reset_index(drop=True)

LAND_LEVEL1 = [
    ('1. Territorios artificializados', '#bdbdbd', 'Territorios artificializados'),
    ('2. Territorios agrícolas', '#f1b82d', 'Territorios agrícolas (denominador)'),
    ('3. Bosques y medios seminaturales', '#276419', 'Bosques y medios seminaturales'),
    ('4. Zonas húmedas', '#66c2a5', 'Zonas húmedas'),
    ('5. Cuerpos de agua', '#2b8cbe', 'Cuerpos de agua'),
]

def raw_polygons(target_crs):
    """Read MAGA polygons only for display; aggregation continues to use CODIGO."""
    u=gpd.read_file(SHP)
    u=u.loc[pd.to_numeric(u.CODIGO,errors='coerce').fillna(-1).astype(int).ne(0)].copy()
    if not {'Nivel_1','USOT','Area_Ha_Aj'}.issubset(u.columns): raise ValueError('MAGA display fields unavailable')
    u.loc[~u.geometry.is_valid,'geometry']=u.loc[~u.geometry.is_valid,'geometry'].map(make_valid)
    if u.crs is None: raise ValueError('MAGA display geometry has no CRS')
    return u.to_crs(target_crs)

def raw_draw(ax,u,g,kind,title,*,department_borders=False):
    """Draw source polygons, never an aggregation to municipality."""
    if kind=='land_cover':
        for value,color,label in LAND_LEVEL1:
            u.loc[u.Nivel_1.eq(value)].plot(ax=ax,color=color,edgecolor='none',linewidth=0,rasterized=True,zorder=1)
        legend=[Patch(facecolor=color,edgecolor='#555555',linewidth=.35,label=label) for _,color,label in LAND_LEVEL1]
    elif kind=='agricultural_land':
        # Raw MAGA agricultural polygons are coloured; the grey background is only a country outline.
        g.plot(ax=ax,color='#e6e6e6',edgecolor='none',linewidth=0,zorder=1)
        u.loc[u.Nivel_1.eq('2. Territorios agrícolas')].plot(ax=ax,color='#f1b82d',edgecolor='none',linewidth=0,rasterized=True,zorder=2)
        legend=[Patch(facecolor='#f1b82d',edgecolor='#555555',linewidth=.35,label='Territorios agrícolas (Nivel 1)'),Patch(facecolor='#e6e6e6',edgecolor='#555555',linewidth=.35,label='Otras áreas del país')]
    elif kind=='maize_bean':
        # The background is the national outline; only the source crop polygons are drawn in colour.
        # This keeps a raw-polygon view without creating a 100,000-polygon grey layer.
        g.plot(ax=ax,color='#e6e6e6',edgecolor='none',linewidth=0,zorder=1)
        u.loc[u.USOT.eq('Maíz y frijol')].plot(ax=ax,color='#d95f0e',edgecolor='none',linewidth=0,rasterized=True,zorder=2)
        legend=[Patch(facecolor='#d95f0e',edgecolor='#555555',linewidth=.35,label='Maíz y frijol'),Patch(facecolor='#e6e6e6',edgecolor='#555555',linewidth=.35,label='Otras áreas del país')]
    else: raise ValueError(kind)
    g.boundary.plot(ax=ax,color='white',linewidth=.10,alpha=.55,zorder=5)
    if department_borders: g.dissolve(by='Departamento').boundary.plot(ax=ax,color='#111111',linewidth=.72,zorder=7)
    cap=g.loc[g.codigo_municipio_4d.eq('0101')].to_crs('EPSG:6933').copy(); cap['geometry']=cap.centroid
    cap.to_crs(g.crs).plot(ax=ax,marker='*',color='#111111',edgecolor='white',linewidth=.65,markersize=48,zorder=8)
    ax.text(0,1.012,title,transform=ax.transAxes,fontsize=10.8,fontweight='bold',va='bottom',linespacing=1.12)
    ax.set_axis_off(); ax.set_aspect('equal')
    return legend+[Line2D([0],[0],marker='*',color='white',markerfacecolor='#111111',markeredgecolor='white',markersize=7.4,label='Ciudad de Guatemala')]

def raw_wide_map(u,g,kind,title,legend_title,stem,*,department_borders=False,destination=None):
    fig,ax=plt.subplots(figsize=(7.15,3.75),facecolor='white'); legend=raw_draw(ax,u,g,kind,title,department_borders=department_borders)
    leg=ax.legend(handles=legend,title=legend_title,loc='lower center',bbox_to_anchor=(.5,-.02),fontsize=7.8,title_fontsize=7.8,frameon=False,ncol=3,columnspacing=.80,labelspacing=.34,handlelength=1.03); leg._legend_box.align='left'
    fig.subplots_adjust(left=.015,right=.985,top=.89,bottom=.028)
    if destination is None: save(fig,BODY/(stem+'_body.pdf'),PROJECT/'figures'/(stem+'.png'),True)
    else: save(fig,destination)

def worker_wide_map(g,*,department_borders=False,destination=None):
    bins=[-np.inf,25,50,100,200,400,np.inf]; labels=['<25','25--50','50--100','100--200','200--400','$\\geq$400']
    fig,ax=plt.subplots(figsize=(7.15,3.75),facecolor='white')
    draw(ax,g,'ag_workers_per_100_agricultural_ha',bins,labels,'b. Trabajadores agrícolas por 100 ha de tierra agrícola cartografiada\nCenso 2018 y MAGA 2025',head=10.8,department_borders=department_borders)
    leg=ax.legend(handles=handles(labels),title='Trabajadores por 100 ha',loc='lower center',bbox_to_anchor=(.5,-.02),fontsize=7.8,title_fontsize=7.8,frameon=False,ncol=4,columnspacing=.75,labelspacing=.34,handlelength=1.03); leg._legend_box.align='left'
    fig.subplots_adjust(left=.015,right=.985,top=.89,bottom=.028)
    if destination is None: save(fig,BODY/'fig07b_ine_agriculture_workers_usable_land_wide_body.pdf',PROJECT/'figures'/'fig07b_ine_agriculture_workers_usable_land_wide.png',True)
    else: save(fig,destination)

def raw_tall_map(u,g,kind,title,legend_title,stem,*,department_borders=False,destination=None):
    fig,ax=plt.subplots(figsize=(6.1,6.35),facecolor='white'); legend=raw_draw(ax,u,g,kind,title,department_borders=department_borders)
    leg=ax.legend(handles=legend,title=legend_title,loc='lower left',fontsize=9.2,title_fontsize=9.2,frameon=False,ncol=2,columnspacing=.72,labelspacing=.35,handlelength=1.05); leg._legend_box.align='left'
    fig.subplots_adjust(left=.025,right=.975,top=.91,bottom=.025)
    if destination is None: save(fig,BODY/(stem+'_body.pdf'),PROJECT/'figures'/(stem+'.png'),True)
    else: save(fig,destination)

def municipal_metrics(m):
    """Merge employment/land exposure with common-reference CHIRPS shocks for all 340 municipalities."""
    current=pd.read_csv(DERIVED/'chirps_2026_municipality.csv')
    current['codigo_municipio_4d']=pd.to_numeric(current.municipality_id,errors='raise').astype(int).astype(str).str.zfill(4)
    current_cols=['codigo_municipio_4d','historical_mean_may_aug_mm','historical_sd_may_aug_mm',
                  'rain_2026_may_aug_mm','rainfall_z_score_vs_1981_2025']
    x=m.merge(current[current_cols],on='codigo_municipio_4d',validate='one_to_one')
    historic=pd.read_csv(APP/'chirps_common_reference_zscore_2015_2019_2025_municipality.csv')
    historic=historic.loc[historic.year.eq(2015),['municipality_id','rainfall_z_score_common']].copy()
    historic['codigo_municipio_4d']=pd.to_numeric(historic.municipality_id,errors='raise').astype(int).astype(str).str.zfill(4)
    historic=historic.rename(columns={'rainfall_z_score_common':'z_2015_common'})[['codigo_municipio_4d','z_2015_common']]
    x=x.merge(historic,on='codigo_municipio_4d',validate='one_to_one')
    x['z_2026_common']=x.rainfall_z_score_vs_1981_2025
    x['impact_composite']=np.maximum(-x.z_2026_common,0)*x.ag_workers_per_100_agricultural_ha
    x['impact_composite_2015']=np.maximum(-x.z_2015_common,0)*x.ag_workers_per_100_agricultural_ha
    if len(x)!=340: raise ValueError('Expected 340 municipal rows in impact table')
    return x.sort_values(['impact_composite','Departamento','Municipio'],ascending=[False,True,True]).reset_index(drop=True)


def field_rows(m):
    x=municipal_metrics(m)
    x['key']=x.Departamento.map(norm); x['municipality_key']=x.Municipio.map(norm)
    x=x.loc[x.municipality_key.isin({'CHAHAL','OLOPA','PATZITE'})].copy()
    if len(x)!=3: raise ValueError('Expected Chahal, Olopa, and Patzité in municipal table')
    return x.sort_values(['key','municipality_key'])


def tex_escape(x):
    return str(x).replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')


def table(d,m):
    """Main department table: index components, 2015 comparator, and field-site subrows."""
    sites=field_rows(m); by_department={key: chunk for key,chunk in sites.groupby('key')}
    def current_z(value): return rf'\cellcolor{{currentz}}\textbf{{{value:.2f}}}'
    def impact(value): return rf'\cellcolor{{impactlight}}\underline{{\textbf{{{value:.1f}}}}}'
    def oxfam(value): return '---' if pd.isna(value) else rf'\cellcolor{{oxfamlite}}\underline{{\textbf{{{value:.2f}}}}}'
    rows=[]
    for r in d.itertuples(index=False):
        rows.append(
            f'{tex_escape(r.Departamento)} & {r.hist_mean_mm:.0f} ({r.hist_sd_mm:.0f}) & {r.rain_2026_mm:.0f} & '
            f'{current_z(r.z_2026_common)} & {r.agricultural_workers:,.0f} & {r.agricultural_land_ha:,.0f} & '
            f'{impact(r.impact_composite)} & {oxfam(r.oxfam_households_with_losses_pct)} & {r.z_2015_common:.2f} & {r.impact_composite_2015:.1f} ' + r'\\')
        for q in by_department.get(r.key,sites.iloc[0:0]).itertuples(index=False):
            rows.append(
                f'\\rowcolor{{sitegray}}\\quad\\textit{{{tex_escape(q.Municipio)} (municipio)}} & '
                f'{q.historical_mean_may_aug_mm:.0f} ({q.historical_sd_may_aug_mm:.0f}) & {q.rain_2026_may_aug_mm:.0f} & '
                f'{current_z(q.z_2026_common)} & {q.A:,.0f} & {q.agricultural_land_ha:,.0f} & '
                f'{impact(q.impact_composite)} & --- & {q.z_2015_common:.2f} & {q.impact_composite_2015:.1f} ' + r'\\')
    content = r"""\begin{landscape}
\thispagestyle{jpal}
\definecolor{currentz}{HTML}{F9D9D2}
\definecolor{impactlight}{HTML}{EAD1CD}
\definecolor{oxfamlite}{HTML}{FFF0BF}
\definecolor{sitegray}{HTML}{F3F3F3}
\begin{center}
\refstepcounter{table}\label{tab:departmental-agricultural-drought-summary}
{\small\textbf{Tabla \thetable. Sequía, exposición agrícola e índice de impacto, por departamento}\par}
\vspace{4pt}
\scriptsize
\begin{tabular}{@{}lrrrrrrrrr@{}}
\toprule
& \multicolumn{3}{c}{\textbf{Sequía}} & \multicolumn{2}{c}{\textbf{Exposición agrícola}} & \multicolumn{1}{c}{\textbf{\underline{Índice}}} & \multicolumn{1}{c}{\textbf{\underline{Pérdidas}}} & \multicolumn{2}{c}{\textbf{Comparación 2015}} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-6}\cmidrule(lr){7-7}\cmidrule(lr){8-8}\cmidrule(lr){9-10}
Departamento / municipio & \shortstack{Media hist.\\(DE)} & \shortstack{Lluvia\\2026} & \shortstack{$z_{2026}$\\actual} & \shortstack{Trab. agrícolas\\INE 2018} & \shortstack{ha agrícolas\\MAGA 2025} & \shortstack{\underline{Índice de impacto}\\$[-z_{2026}]_+\times$ trab.\\ag./100 ha} & \shortstack{\underline{Pérdidas reportadas}\\\underline{Oxfam 2026} (\%)} & $z_{2015}$ & \shortstack{Índice\\2015} \\
\midrule
"""+'\n'.join(rows)+r"""
\bottomrule
\end{tabular}
\vspace{5pt}
\begin{minipage}{0.97\linewidth}
\scriptsize\RaggedRight\textit{Notas.} Fuentes: CHIRPS v3 (mayo--agosto), INE, Censo 2018, cuadro A12.2, MAGA, cobertura vegetal y uso de la tierra 2025, y Oxfam. Media histórica y DE corresponden a 1981--2025. Los dos z-scores usan esa misma referencia local; el de 2026 se sombrea para distinguir el shock actual. ``ha agrícolas'' es el área MAGA clasificada como Nivel 1 ``Territorios agrícolas''; es el denominador disponible para la medida y no equivale a tierra arable, sembrada o productiva. Índice de impacto = $\max(-z,0)\times(100A/\mathrm{ha}^{ag})$, una clasificación descriptiva, no una estimación de pérdidas ni causal. El índice y los porcentajes Oxfam disponibles se subrayan; las filas grises son municipios de campo dentro de su departamento. El índice 2015 aplica la misma exposición laboral y de cobertura MAGA al z-score de 2015, para permitir comparación mecánica de severidad/exposición.
\end{minipage}
\end{center}
\end{landscape}
"""
    out=PROJECT/'overleaf/assets/tables/table_departmental_agricultural_drought_summary_body.tex'
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(content,encoding='utf-8')


def municipal_table(m):
    """Standalone longtable for supplemental.tex; ordered by the 2026 impact index."""
    x=municipal_metrics(m)
    rows=[]
    for r in x.itertuples(index=False):
        rows.append(
            f'{tex_escape(r.Municipio)} ({tex_escape(r.Departamento)}) & {r.historical_mean_may_aug_mm:.0f} ({r.historical_sd_may_aug_mm:.0f}) & '
            f'{r.rain_2026_may_aug_mm:.0f} & \\cellcolor{{currentz}}\\textbf{{{r.z_2026_common:.2f}}} & {r.A:,.0f} & '
            f'{r.agricultural_land_ha:,.0f} & \\cellcolor{{impactlight}}\\underline{{\\textbf{{{r.impact_composite:.1f}}}}} & '
            f'{r.z_2015_common:.2f} & {r.impact_composite_2015:.1f} ' + r'\\')
    content=r"""\begin{landscape}
\definecolor{currentz}{HTML}{F9D9D2}
\definecolor{impactlight}{HTML}{EAD1CD}
\scriptsize
\setlength{\LTleft}{0pt plus 1fill}
\setlength{\LTright}{0pt plus 1fill}
\begin{longtable}{@{}lrrrrrrrr@{}}
\caption{Tabla S1. Sequía, exposición agrícola e índice de impacto por municipio, ordenado por índice 2026}\label{tab:municipal-agricultural-drought-summary}\\
\toprule
& \multicolumn{3}{c}{\textbf{Sequía}} & \multicolumn{2}{c}{\textbf{Exposición agrícola}} & \multicolumn{1}{c}{\textbf{\underline{Índice}}} & \multicolumn{2}{c}{\textbf{Comparación 2015}} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-6}\cmidrule(lr){7-7}\cmidrule(lr){8-9}
Municipio (departamento) & \shortstack{Media hist.\\(DE)} & \shortstack{Lluvia\\2026} & \shortstack{$z_{2026}$\\actual} & \shortstack{Trab. agrícolas\\INE 2018} & \shortstack{ha agrícolas\\MAGA 2025} & \shortstack{\underline{Índice de impacto}\\$[-z_{2026}]_+\times$ trab.\\ag./100 ha} & $z_{2015}$ & \shortstack{Índice\\2015} \\
\midrule
\endfirsthead
\multicolumn{9}{c}{\small\textit{Tabla S1. Continúa}}\\
\toprule
& \multicolumn{3}{c}{\textbf{Sequía}} & \multicolumn{2}{c}{\textbf{Exposición agrícola}} & \multicolumn{1}{c}{\textbf{\underline{Índice}}} & \multicolumn{2}{c}{\textbf{Comparación 2015}} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-6}\cmidrule(lr){7-7}\cmidrule(lr){8-9}
Municipio (departamento) & \shortstack{Media hist.\\(DE)} & \shortstack{Lluvia\\2026} & \shortstack{$z_{2026}$\\actual} & \shortstack{Trab. agrícolas\\INE 2018} & \shortstack{ha agrícolas\\MAGA 2025} & \shortstack{\underline{Índice de impacto}\\$[-z_{2026}]_+\times$ trab.\\ag./100 ha} & $z_{2015}$ & \shortstack{Índice\\2015} \\
\midrule
\endhead
\midrule
\multicolumn{9}{r}{\textit{Continúa en la página siguiente}}\\
\endfoot
\bottomrule
\multicolumn{9}{@{}p{\linewidth}@{}}{\scriptsize\RaggedRight\textit{Notas.} Fuentes: CHIRPS v3, INE, Censo 2018, cuadro A12.2, y MAGA, cobertura vegetal y uso de la tierra 2025. Media histórica y DE: 1981--2025. Los z-scores de 2015 y 2026 usan la misma referencia local. ``ha agrícolas'' = área MAGA Nivel 1 ``Territorios agrícolas''; no equivale a tierra arable, sembrada o productiva. Índice 2026 = $\max(-z_{2026},0)\times(100A/\mathrm{ha}^{ag})$; índice 2015 aplica el mismo denominador de empleo/cobertura al z-score 2015. Es una clasificación descriptiva, no una estimación de pérdidas ni causal.}\\
\endlastfoot
"""+'\n'.join(rows)+r"""
\end{longtable}
\end{landscape}
"""
    out=PROJECT/'overleaf/assets/tables/table_municipal_agricultural_drought_summary_supplemental.tex'
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(content,encoding='utf-8')
    x.to_csv(DERIVED/'municipal_agricultural_drought_impact_2026_2015.csv',index=False)

def exploration(g):
    specs=[
      ('agricultural_land_share_of_mapped_pct',[-np.inf,15,30,45,60,75,np.inf],['<15%','15--30%','30--45%','45--60%','60--75%','$\geq$75%'],'Tierra agrícola cartografiada / área cartografiada','Porcentaje','01_participacion_tierra_agricola_cartografiada'),
      ('maize_bean_ha',[-np.inf,250,1000,2500,5000,10000,np.inf],['<250','250--1 mil','1--2,5 mil','2,5--5 mil','5--10 mil','$\geq$10 mil'],'Área cartografiada: maíz y frijol','Hectáreas','02_area_maiz_frijol'),
      ('maize_bean_share_of_agricultural_land_pct',[-np.inf,5,15,30,50,70,np.inf],['<5%','5--15%','15--30%','30--50%','50--70%','$\geq$70%'],'Maíz y frijol como parte de tierra agrícola','Porcentaje','03_maiz_frijol_participacion_tierra_agricola')]
    for var,bins,labels,title,legend,stem in specs:
        fig,ax=plt.subplots(figsize=(6.1,6.35),facecolor='white'); draw(ax,g,var,bins,labels,title); ax.legend(handles=handles(labels),title=legend,loc='lower left',fontsize=9.65,title_fontsize=9.65,frameon=False,ncol=3,columnspacing=.7,labelspacing=.35,handlelength=1.05); fig.subplots_adjust(left=.025,right=.975,top=.91,bottom=.025); save(fig,OUTPUT/(stem+'.pdf'),OUTPUT/(stem+'.png'))

def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'ps.fonttype':42})
    g=geo(); m=aggregate(g); DERIVED.mkdir(parents=True,exist_ok=True); OUTPUT.mkdir(parents=True,exist_ok=True); DEPARTMENT_EXPORTS.mkdir(parents=True,exist_ok=True)
    m.sort_values('codigo_municipio_4d').to_csv(DERIVED/'maga_uso_tierra_2025_municipality_metrics.csv',index=False)
    d=department(m); d.to_csv(DERIVED/'maga_uso_tierra_2025_department_metrics.csv',index=False)
    z=g.merge(m.drop(columns=['Departamento','Municipio']),on='codigo_municipio_4d',validate='one_to_one'); u=raw_polygons(g.crs)
    raw_wide_map(u,g,'land_cover','a. Cobertura y uso de la tierra: denominador agrícola\nMAGA 2025','Clase MAGA Nivel 1','fig07a_maga_land_use_denominator')
    worker_wide_map(z)
    raw_tall_map(u,g,'agricultural_land','Polígonos MAGA clasificados como territorios agrícolas\nMAGA 2025','Cobertura MAGA','appendix_app03_maga_agricultural_land_polygons')
    raw_tall_map(u,g,'maize_bean','Polígonos cartografiados de maíz y frijol\nMAGA 2025','Uso/cobertura MAGA','fig08_maga_maize_bean_area')
    main_map(z,'ag_workers_per_100_agricultural_ha',[-np.inf,25,50,100,200,400,np.inf],['<25','25--50','50--100','100--200','200--400','$\geq$400'],'Trabajadores agrícolas por 100 ha de tierra agrícola cartografiada\nCenso 2018 y MAGA 2025','Trabajadores por 100 ha','fig06b_ine_agriculture_workers_usable_land')
    exploration(z); table(d,m); municipal_table(m)
    raw_wide_map(u,g,'land_cover','Cobertura y uso de la tierra: denominador agrícola\nMAGA 2025','Clase MAGA Nivel 1','unused',department_borders=True,destination=DEPARTMENT_EXPORTS/'figura_07a_cobertura_maga_fronteras_departamentales.pdf')
    worker_wide_map(z,department_borders=True,destination=DEPARTMENT_EXPORTS/'figura_07b_trabajadores_por_tierra_fronteras_departamentales.pdf')
    raw_tall_map(u,g,'agricultural_land','Polígonos MAGA clasificados como territorios agrícolas\nMAGA 2025','Cobertura MAGA','unused',department_borders=True,destination=DEPARTMENT_EXPORTS/'apendice_territorios_agricolas_maga_fronteras_departamentales.pdf')
    raw_tall_map(u,g,'maize_bean','Polígonos cartografiados de maíz y frijol\nMAGA 2025','Uso/cobertura MAGA','unused',department_borders=True,destination=DEPARTMENT_EXPORTS/'figura_08_maiz_frijol_fronteras_departamentales.pdf')
    main_map(z,'ag_workers_per_100_agricultural_ha',[-np.inf,25,50,100,200,400,np.inf],['<25','25--50','50--100','100--200','200--400','$\geq$400'],'Trabajadores agrícolas por 100 ha de tierra agrícola cartografiada\nCenso 2018 y MAGA 2025','Trabajadores por 100 ha','unused',department_borders=True,destination=DEPARTMENT_EXPORTS/'figura_07b_municipal_fronteras_departamentales.pdf')
    (OUTPUT/'README.md').write_text("""# Exploración geográfica — cobertura vegetal y uso de la tierra 2025 (MAGA)

Generado por `python3 code/build_maga_land_use_maps.py`. La fuente cruda permanece inmutable. Cada polígono ya trae `CODIGO`; se excluyen los polígonos lacustres con código 0 y se agregan `Area_Ha_Aj` por código municipal. El resultado valida exactamente los 340 municipios del TopoJSON analítico existente.

- `01_participacion_tierra_agricola_cartografiada`: tierra de Nivel 1 `2. Territorios agrícolas` como parte del área cartografiada.
- `02_area_maiz_frijol`: hectáreas de la única clase explícita `Maíz y frijol`.
- `03_maiz_frijol_participacion_tierra_agricola`: dicha clase como parte de tierra agrícola cartografiada.
- Los mapas del informe muestran además los polígonos crudos de cobertura/uso y la clase conjunta `Maíz y frijol`, sin agregarlos a municipio.

La capa identifica maíz y frijol conjuntamente: no permite separar hectáreas de cada cultivo. Tierra agrícola cartografiada es un denominador de cobertura/uso de suelo, no tierra sembrada, productividad ni tierra económicamente utilizable observada. El SHP no clasifica áreas protegidas como una categoría separada.
""",encoding='utf-8')
    print(f'MAGA outputs: {len(m)} municipalities; {len(d)} departments; raw polygons={len(u):,}.')

if __name__ == '__main__': main()
