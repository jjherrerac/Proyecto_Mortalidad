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

