GIROS = [
    ("CHOCOLATE_ARTESANAL", "Chocolate artesanal"),
    ("CACAO_Y_DERIVADOS", "Cacao y derivados"),
    ("REPOSTERIA", "Repostería"),
    ("BEBIDAS_TRADICIONALES", "Bebidas tradicionales"),
    ("GASTRONOMIA_TABASQUENA", "Gastronomía tabasqueña"),
    ("ARTESANIAS", "Artesanías"),
    ("TURISMO_EXPERIENCIAS", "Turismo y experiencias"),
    ("MODA_Y_DISENO", "Moda y diseño"),
    ("TECNOLOGIA_LOCAL", "Tecnología local"),
    ("SERVICIOS_EMPRESARIALES", "Servicios empresariales"),
]

SUBGIROS_POR_GIRO = {
    "CHOCOLATE_ARTESANAL": [("BARRAS_CHOCOLATE", "Barras y tabletas"), ("BOMBONERIA", "Bombonería y confitería"), ("CHOCOLATE_MESA", "Chocolate de mesa")],
    "CACAO_Y_DERIVADOS": [("CACAO_GRANO", "Cacao en grano"), ("DERIVADOS_CACAO", "Derivados del cacao"), ("COSMETICA_CACAO", "Cosmética a base de cacao")],
    "REPOSTERIA": [("PANADERIA", "Panadería"), ("PASTELERIA", "Pastelería"), ("POSTRES", "Postres y dulces")],
    "BEBIDAS_TRADICIONALES": [("BEBIDAS_CACAO", "Bebidas de cacao"), ("BEBIDAS_REGIONALES", "Bebidas regionales"), ("BEBIDAS_ARTESANALES", "Bebidas artesanales")],
    "GASTRONOMIA_TABASQUENA": [("ALIMENTOS_PREPARADOS", "Alimentos preparados"), ("SALSAS_CONSERVAS", "Salsas y conservas"), ("PRODUCTOS_REGIONALES", "Productos regionales")],
    "ARTESANIAS": [("TEXTILES", "Textiles"), ("MADERA_FIBRAS", "Madera y fibras naturales"), ("JOYERIA_ARTESANAL", "Joyería artesanal")],
    "TURISMO_EXPERIENCIAS": [("TOURS", "Tours y recorridos"), ("HOSPEDAJE", "Hospedaje"), ("EXPERIENCIAS", "Experiencias turísticas")],
    "MODA_Y_DISENO": [("ROPA", "Ropa"), ("ACCESORIOS", "Accesorios"), ("DISENO_LOCAL", "Diseño local")],
    "TECNOLOGIA_LOCAL": [("SOFTWARE", "Software"), ("EQUIPOS", "Equipos y dispositivos"), ("SERVICIOS_DIGITALES", "Servicios digitales")],
    "SERVICIOS_EMPRESARIALES": [("CONSULTORIA", "Consultoría"), ("CAPACITACION", "Capacitación"), ("SERVICIOS_PROFESIONALES", "Servicios profesionales")],
}

SUBGIROS = [(dict(GIROS)[giro], opciones) for giro, opciones in SUBGIROS_POR_GIRO.items()]

PROGRAMAS_ESPECIALES = [
    ("NINGUNO", "No pertenezco a un programa social"),
    ("ORIGEN_TABASCO", "Origen Tabasco"),
    ("TANDAS_MUJER", "Tandas para la Mujer"),
    ("CODIGO_BARRAS", "Código de Barras"),
]

EVENTO_NOMBRE = "Festival del Chocolate"

EVENTO_INFO = {
    "nombre": EVENTO_NOMBRE,
    "imagen": "img/others/CHOCOLATE.png",
    "descripcion": (
        "Participa en el Festival del Chocolate y presenta tu comercio, "
        "productos y propuesta ante visitantes y expositores."
    ),
    "estado": "Convocatoria disponible",
    "categoria": "FERIA",
}
