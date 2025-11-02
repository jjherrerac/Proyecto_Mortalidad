# Panel de Mortalidad — Colombia (Demo)

## 👥 Integrantes del grupo
- **John Jairo Herrera Cardona**
- **Erley Fabián Valencia Carvajal**

---

## 🌐 URL de la aplicación desplegada
🔗 [https://proyecto-mortalidad.onrender.com](https://proyecto-mortalidad.onrender.com)

## 💾 URL del repositorio en GitHub
🔗 [https://github.com/jjherrearc/Proyecto_Mortalidad](https://github.com/jjherrearc/Proyecto_Mortalidad)

---

## 🧩 Introducción del proyecto
El **Panel de Mortalidad — Colombia** es una aplicación web interactiva desarrollada en **Python con Dash** que tiene como propósito principal **visualizar, analizar y comprender los patrones de mortalidad en Colombia** a partir de datos oficiales.  

A través de gráficos dinámicos y tablas, la aplicación permite explorar de manera intuitiva las principales causas de fallecimiento, su distribución por sexo, edad y región, así como la evolución mensual de los casos.  

El proyecto fue desarrollado en el marco de una actividad académica orientada al aprendizaje práctico del despliegue de aplicaciones analíticas en la nube mediante plataformas **PaaS (Platform as a Service)** como **Render**, y a la gestión profesional del código a través de **GitHub**.

---

## 🎯 Objetivo
El objetivo del proyecto es **crear una herramienta visual e interactiva** que facilite el análisis de la mortalidad en Colombia desde diferentes perspectivas demográficas y epidemiológicas.  

De forma específica, se busca:
- Identificar las **10 principales causas de muerte** en el país.  
- Comparar las muertes según **sexo biológico** (hombres y mujeres).  
- Analizar la **distribución de casos por grupo etario** según las clasificaciones del DANE.  
- Visualizar las **tendencias mensuales** de mortalidad a lo largo del año.  
- Aplicar buenas prácticas de **desarrollo, documentación y despliegue** en entornos web.

---

## 🏗 Estructura del proyecto
```
Proyecto_Mortalidad/
│
├── app.py                  # Código principal de la aplicación Dash
├── requirements.txt        # Librerías y versiones necesarias
├── render.yaml             # Archivo de configuración para el despliegue en Render
├── data/                   # Carpeta con los datos utilizados
│   ├── departamentos.geojson
│   ├── Anexo1NoFetal2019_CE_15_04_2020.xlsx
│   ├── Anexo2CodigosDeMuerte_CE_15_04_2020.xlsx
│
├── images/                 # Capturas del panel (opcional)
│   ├── panel_general.png
│   ├── causas_top10.png
│   ├── distribucion_edad.png
│   ├── tendencia_mensual.png
│
└── README.md               # Documento explicativo del proyecto
```

**Visualizaciones y explicaciones de los resultados**

1️⃣ Visión general

Muestra un mapa interactivo de los departamentos de Colombia con el número total de muertes y gráficos complementarios que resumen la información global.

2️⃣ Municipios (gráfico de torta)

Representa la participación porcentual de los municipios en el total de muertes por departamento.

3️⃣ Causas (Top 10)

Presenta una tabla interactiva con las 10 principales causas de muerte, ordenadas de mayor a menor número de casos.
Cada fila incluye el código DANE, el nombre de la causa y el total de fallecimientos.

4️⃣ Muertes por sexo

Gráfico de barras apiladas que compara el número de muertes en hombres y mujeres.

5️⃣ Distribución por edad (histograma)

Muestra la cantidad de muertes según los grupos etarios definidos por el DANE (neonatal, infantil, niñez, juventud, adultez, vejez, longevidad, etc.).

6️⃣ Tendencia mensual (líneas)

Gráfico de líneas que representa la variación de muertes a lo largo del año, permitiendo observar picos o descensos estacionales.



**Software y herramientas utilizadas**

Python: Lenguaje principal de programación.

Dash (Plotly): Framework para construir interfaces analíticas interactivas.

Pandas: Manejo y transformación de datos tabulares.

Plotly Express: Generación de gráficos interactivos.

OpenPyXL: Lectura de datos en formato Excel.

Gunicorn: Servidor de aplicaciones WSGI para producción.

Render: Plataforma de despliegue en la nube (PaaS).

GitHub: Control de versiones y repositorio remoto del proyecto.


