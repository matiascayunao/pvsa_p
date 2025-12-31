from django.forms import ModelForm, formset_factory
from django import forms
from .models import (
    Sector,
    Ubicacion,
    Piso,
    Lugar,
    TipoLugar,
    TipoObjeto,
    CategoriaObjeto,
    ObjetoLugar,
    Objeto,
    HistoricoObjeto,
)

# -------------------
# CREAR
# -------------------


class CrearSector(ModelForm):
    class Meta:
        model = Sector
        fields = ["sector"]


class CrearUbicacion(ModelForm):
    class Meta:
        model = Ubicacion
        fields = ["ubicacion", "sector"]


class CrearPiso(ModelForm):
    class Meta:
        model = Piso
        fields = ["piso", "ubicacion"]


class CrearLugar(ModelForm):
    class Meta:
        model = Lugar
        fields = ["nombre_del_lugar", "piso", "lugar_tipo_lugar"]


class CrearObjetoLugar(forms.ModelForm):
    class Meta:
        model = ObjetoLugar
        fields = ["tipo_de_objeto", "cantidad", "estado", "detalle"]
        widgets = {
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "detalle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Detalle (opcional)"}
            ),
        }


class CrearTipoLugar(ModelForm):
    class Meta:
        model = TipoLugar
        fields = ["tipo_de_lugar"]


class CrearCategoriaObjeto(ModelForm):
    class Meta:
        model = CategoriaObjeto
        fields = ["nombre_de_categoria"]


class CrearObjeto(ModelForm):
    class Meta:
        model = Objeto
        fields = ["nombre_del_objeto", "objeto_categoria"]


class CrearTipoObjeto(ModelForm):
    class Meta:
        model = TipoObjeto
        fields = ["objeto", "marca", "material"]


class CrearHistorico(forms.ModelForm):
    fecha_anterior = forms.DateField(
        input_formats=["%d/%m/%Y"],
        widget=forms.DateInput(
            format="%d/%m/%Y",
            attrs={"class": "form-control", "placeholder": "dd/mm/aaaa"},
        ),
    )

    class Meta:
        model = HistoricoObjeto
        fields = [
            "objeto_del_lugar",
            "cantidad_anterior",
            "estado_anterior",
            "detalle_anterior",
            "fecha_anterior",
        ]
        widgets = {
            "objeto_del_lugar": forms.Select(attrs={"class": "form-select"}),
            "cantidad_anterior": forms.NumberInput(attrs={"class": "form-control"}),
            "estado_anterior": forms.Select(attrs={"class": "form-select"}),
            "detalle_anterior": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["objeto_del_lugar"].disabled = True


# -------------------
# EDITAR
# -------------------


class EditarSector(ModelForm):
    class Meta:
        model = Sector
        fields = ["sector"]


class EditarUbicacion(ModelForm):
    class Meta:
        model = Ubicacion
        fields = ["ubicacion"]


class EditarPiso(ModelForm):
    class Meta:
        model = Piso
        fields = ["piso"]


class EditarTipoLugar(ModelForm):
    class Meta:
        model = TipoLugar
        fields = ["tipo_de_lugar"]


class EditarLugar(ModelForm):
    class Meta:
        model = Lugar
        fields = ["nombre_del_lugar", "piso", "lugar_tipo_lugar"]


class EditarCategoria(ModelForm):
    class Meta:
        model = CategoriaObjeto
        fields = ["nombre_de_categoria"]


class EditarObjeto(ModelForm):
    class Meta:
        model = Objeto
        fields = ["nombre_del_objeto", "objeto_categoria"]


class EditarTipoObjeto(ModelForm):
    class Meta:
        model = TipoObjeto
        fields = ["objeto", "marca", "material"]


class EditarObjetoLugar(forms.ModelForm):
    class Meta:
        model = ObjetoLugar
        fields = ["tipo_de_objeto", "cantidad", "estado", "detalle"]
        widgets = {
            "tipo_de_objeto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "detalle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Detalle (opcional)"}
            ),
        }


class EditarHistorico(ModelForm):
    class Meta:
        model = HistoricoObjeto
        fields = [
            "objeto_del_lugar",
            "cantidad_anterior",
            "estado_anterior",
            "detalle_anterior",
            "fecha_anterior",
        ]


# ============================
# FORMULARIO BASE DE ESTRUCTURA
# ============================

class EstructuraCompletaForm(forms.Form):
    # --- Sector ---
    sector_existente = forms.ModelChoiceField(
        label="Sector (existente)",
        queryset=Sector.objects.all().order_by("sector"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sector_nuevo = forms.CharField(
        label="Nuevo sector",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # --- Ubicación ---
    ubicacion_existente = forms.ModelChoiceField(
        label="Ubicación (existente)",
        queryset=Ubicacion.objects.select_related("sector")
        .all()
        .order_by("sector__sector", "ubicacion"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ubicacion_nueva = forms.CharField(
        label="Nueva ubicación",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # --- Piso ---
    piso_existente = forms.ModelChoiceField(
        label="Piso (existente)",
        queryset=Piso.objects.select_related("ubicacion")
        .all()
        .order_by("ubicacion__ubicacion", "piso"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    piso_nuevo = forms.IntegerField(
        label="Nuevo piso",
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    # --- Tipo de lugar ---
    tipo_lugar_existente = forms.ModelChoiceField(
        label="Tipo de lugar (existente)",
        queryset=TipoLugar.objects.all().order_by("tipo_de_lugar"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    tipo_lugar_nuevo = forms.CharField(
        label="Nuevo tipo de lugar",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # --- Nombre del lugar (siempre a mano) ---
    nombre_del_lugar = forms.CharField(
        label="Nombre del lugar",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()

        # Sector: existente o nuevo
        if not cleaned.get("sector_existente") and not (cleaned.get("sector_nuevo") or "").strip():
            raise forms.ValidationError(
                "Debes seleccionar un sector existente o escribir uno nuevo."
            )

        # Ubicación: existente o nueva
        if not cleaned.get("ubicacion_existente") and not (cleaned.get("ubicacion_nueva") or "").strip():
            raise forms.ValidationError(
                "Debes seleccionar una ubicación existente o escribir una nueva."
            )

        # Piso: existente o nuevo
        if not cleaned.get("piso_existente") and cleaned.get("piso_nuevo") in (None, ""):
            raise forms.ValidationError(
                "Debes seleccionar un piso existente o escribir uno nuevo."
            )

        # Tipo de lugar: existente o nuevo
        if not cleaned.get("tipo_lugar_existente") and not (cleaned.get("tipo_lugar_nuevo") or "").strip():
            raise forms.ValidationError(
                "Debes seleccionar un tipo de lugar existente o escribir uno nuevo."
            )

        return cleaned


# ============================
# FORMULARIO DE FILA DE OBJETO
# ============================

class ObjetoLugarFilaForm(forms.Form):
    # --- Categoría ---
    categoria_existente = forms.ModelChoiceField(
        label="Categoría (existente)",
        queryset=CategoriaObjeto.objects.all().order_by("nombre_de_categoria"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    categoria_nueva = forms.CharField(
        label="Nueva categoría",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )

    # --- Objeto ---
    objeto_existente = forms.ModelChoiceField(
        label="Objeto (existente)",
        queryset=Objeto.objects.select_related("objeto_categoria")
        .all()
        .order_by("objeto_categoria__nombre_de_categoria", "nombre_del_objeto"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    objeto_nuevo = forms.CharField(
        label="Nuevo objeto",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )

    # --- Tipo de objeto ---
    tipo_objeto_existente = forms.ModelChoiceField(
        label="Tipo de objeto (existente)",
        queryset=TipoObjeto.objects.select_related("objeto")
        .all()
        .order_by("objeto__nombre_del_objeto", "marca", "material"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    marca = forms.CharField(
        label="Marca",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )
    material = forms.CharField(
        label="Material",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )

    # --- Datos del objeto en el lugar ---
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control form-control-sm", "style": "width: 80px;"}
        ),
    )
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=ObjetoLugar.ESTADO,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    detalle = forms.CharField(
        label="Detalle",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )

    def clean(self):
        cleaned = super().clean()

        # ¿Fila completamente vacía? -> la marcamos y la vista la ignora
        fields_to_check = [
            "categoria_existente", "categoria_nueva",
            "objeto_existente", "objeto_nuevo",
            "tipo_objeto_existente", "marca", "material",
            "cantidad", "estado", "detalle",
        ]
        if not any(cleaned.get(f) not in (None, "", 0) for f in fields_to_check):
            cleaned["__empty__"] = True
            return cleaned

        # A partir de aquí, la fila se considera "usada", así que validamos:

        # Categoría: existente o nueva
        if not cleaned.get("categoria_existente") and not (cleaned.get("categoria_nueva") or "").strip():
            raise forms.ValidationError(
                "En cada fila usa una categoría existente o escribe una nueva."
            )

        # Objeto: existente o nuevo
        if not cleaned.get("objeto_existente") and not (cleaned.get("objeto_nuevo") or "").strip():
            raise forms.ValidationError(
                "En cada fila usa un objeto existente o escribe uno nuevo."
            )

        # Tipo de objeto: existente, o marca/material
        tiene_tipo = cleaned.get("tipo_objeto_existente")
        tiene_marca_o_material = (cleaned.get("marca") or "").strip() or (cleaned.get("material") or "").strip()
        if not tiene_tipo and not tiene_marca_o_material:
            pass

        # Cantidad y estado obligatorios si la fila se usa
        if cleaned.get("cantidad") in (None, ""):
            raise forms.ValidationError("En cada fila usada debes indicar la cantidad.")
        if not cleaned.get("estado"):
            raise forms.ValidationError("En cada fila usada debes indicar el estado.")

        cleaned["__empty__"] = False
        return cleaned


ObjetoLugarFilaFormSet = formset_factory(
    ObjetoLugarFilaForm,
    extra=1,
    can_delete=False,
)