from django.db import models, transaction
from django.utils import timezone


class Sector(models.Model):
    sector = models.CharField(max_length=100, unique=True)

    def __str__(self):
        # Solo el nombre del sector
        return self.sector


class Ubicacion(models.Model):
    ubicacion = models.CharField(max_length=100, unique=True)
    sector = models.ForeignKey(
        Sector,
        verbose_name="sector",
        on_delete=models.RESTRICT,
    )

    def __str__(self):
        # Ubicación + sector al que pertenece
        return f"{self.ubicacion} | Sector: {self.sector.sector}"


class Piso(models.Model):
    piso = models.SmallIntegerField()
    ubicacion = models.ForeignKey(
        Ubicacion,
        verbose_name="ubicacion",
        on_delete=models.RESTRICT,
    )

    def __str__(self):
        # Piso + ubicación
        return f"Piso {self.piso} | {self.ubicacion.ubicacion}"


class TipoLugar(models.Model):
    tipo_de_lugar = models.CharField(max_length=100, unique=True)

    def __str__(self):
        # Nombre del tipo de lugar
        return self.tipo_de_lugar


class Lugar(models.Model):
    nombre_del_lugar = models.CharField(max_length=100)
    piso = models.ForeignKey(
        Piso,
        verbose_name="piso",
        on_delete=models.RESTRICT,
    )
    lugar_tipo_lugar = models.ForeignKey(
        TipoLugar,
        verbose_name="tipo de lugar",
        on_delete=models.RESTRICT,
    )

    def __str__(self):
        # Nombre del lugar + piso + ubicación
        return (
            f"{self.nombre_del_lugar} | "
            f"Piso {self.piso.piso} | "
            f"{self.piso.ubicacion.ubicacion}"
        )


class CategoriaObjeto(models.Model):
    nombre_de_categoria = models.CharField(
        max_length=100, verbose_name="categoría", unique=True
    )

    def __str__(self):
        # Solo el nombre de la categoría
        return self.nombre_de_categoria


class Objeto(models.Model):
    nombre_del_objeto = models.CharField(
        max_length=100, verbose_name="objeto", unique=True
    )
    objeto_categoria = models.ForeignKey(
        CategoriaObjeto,
        verbose_name="categoria",
        on_delete=models.RESTRICT,
    )

    def __str__(self):
        # Objeto + categoría entre paréntesis
        return f"{self.nombre_del_objeto} ({self.objeto_categoria.nombre_de_categoria})"


class TipoObjeto(models.Model):
    objeto = models.ForeignKey(
        Objeto,
        verbose_name="objeto",
        on_delete=models.RESTRICT,
    )
    marca = models.CharField(max_length=100, verbose_name="marca", blank=True, null=True)
    material = models.CharField(max_length=100, verbose_name="material", blank=True, null=True)

        

    def __str__(self):
        marca_txt=self.marca.strip() or ""
        material_txt= self.material.strip() or ""

        return f"{self.objeto.nombre_del_objeto} - {marca_txt} {material_txt}".strip()

class TipoLugarObjetoTipico(models.Model):
    tipo_lugar = models.ForeignKey(
        TipoLugar,
        verbose_name="tipo de lugar",
        on_delete=models.CASCADE,
        related_name="tipicos",
    )
    tipo_objeto = models.ForeignKey(
        TipoObjeto,
        verbose_name="tipo de objeto",
        on_delete=models.CASCADE,
        related_name="tipico_en",
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("tipo_lugar", "tipo_objeto")
        ordering = ("orden", "id")

    def __str__(self):
        return f"{self.tipo_lugar.tipo_de_lugar} -> {self.tipo_objeto}"



class ObjetoLugar(models.Model):
    ESTADO = (
        ("B", "Bueno"),
        ("P", "Pendiente"),
        ("M", "Malo"),
    )

    cantidad = models.SmallIntegerField()
    estado = models.CharField(max_length=1, choices=ESTADO)
    detalle = models.CharField(max_length=200, blank=True)
    fecha = models.DateField(auto_now_add=True)

    lugar = models.ForeignKey(
        "Lugar",
        verbose_name="lugar",
        on_delete=models.RESTRICT,
        related_name="objetos_lugar",
        null=True,
        blank=True,
    )

    tipo_de_objeto = models.ForeignKey(
        "TipoObjeto",
        verbose_name="tipo de objeto",
        on_delete=models.RESTRICT,
        related_name="objetos_lugar",
        blank=True,
        null=True
    )

    def __str__(self):
        # Resumen corto: qué objeto es, dónde está y su estado/cantidad
        lugar_txt = (
            f"{self.lugar.nombre_del_lugar} | "
            f"Piso {self.lugar.piso.piso} | {self.lugar.piso.ubicacion.ubicacion}"
            if self.lugar
            else "Sin lugar asignado"
        )
        return (
            f"{self.tipo_de_objeto.objeto.nombre_del_objeto} "
            f"- {self.tipo_de_objeto.marca} {self.tipo_de_objeto.material or ''} "
            f"en {lugar_txt} "
            f"(cant. {self.cantidad}, estado {self.get_estado_display()})"
        )

    def save(self, *args, **kwargs):
        """
        Guarda histórico AUTOMÁTICO solo cuando cambia cantidad/estado/detalle.
        No duplica porque todo se hace aquí, y la vista NO crea Histórico.
        """
        if self.pk:
            anterior = ObjetoLugar.objects.get(pk=self.pk)

            hubo_cambio = (
                anterior.cantidad != self.cantidad
                or anterior.estado != self.estado
                or (anterior.detalle or "") != (self.detalle or "")
            )

            if hubo_cambio:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                    HistoricoObjeto.objects.create(
                        objeto_del_lugar=self,
                        cantidad_anterior=anterior.cantidad,
                        estado_anterior=anterior.estado,
                        detalle_anterior=anterior.detalle or "",
                        fecha_anterior=anterior.fecha,
                    )
                return

        # creación inicial o sin cambios relevantes
        super().save(*args, **kwargs)


class HistoricoObjeto(models.Model):
    # reutilizamos las mismas choices
    ESTADO = ObjetoLugar.ESTADO

    objeto_del_lugar = models.ForeignKey(
        ObjetoLugar,
        verbose_name="objeto del lugar",
        on_delete=models.CASCADE,
        related_name="historicoobjeto",
    )
    cantidad_anterior = models.SmallIntegerField()
    estado_anterior = models.CharField(max_length=1, choices=ESTADO)
    detalle_anterior = models.CharField(max_length=200, blank=True)
    fecha_anterior = models.DateField()

    def __str__(self):
        # Qué objeto es, dónde estaba y cuál era la situación anterior
        obj = self.objeto_del_lugar
        lugar_txt = (
            f"{obj.lugar.nombre_del_lugar} | "
            f"Piso {obj.lugar.piso.piso} | {obj.lugar.piso.ubicacion.ubicacion}"
            if obj.lugar
            else "Sin lugar asignado"
        )
        return (
            f"Histórico de {obj.tipo_de_objeto.objeto.nombre_del_objeto} "
            f"- {obj.tipo_de_objeto.marca} {obj.tipo_de_objeto.material or ''} "
            f"en {lugar_txt} "
            f"(cant. ant. {self.cantidad_anterior}, "
            f"estado ant. {self.get_estado_anterior_display()}, "
            f"fecha {self.fecha_anterior.strftime('%d/%m/%Y')})"
        )