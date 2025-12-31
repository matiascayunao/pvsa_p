from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from .excel_utils import build_excel_sectores
from django.db.models import Sum, Q
from django.views.decorators.http import require_GET

from .forms import (
    CrearSector, CrearUbicacion, CrearPiso, CrearLugar,
    CrearObjetoLugar, CrearTipoLugar, CrearCategoriaObjeto,
    CrearObjeto, CrearTipoObjeto, CrearHistorico,
    EditarSector, EditarUbicacion, EditarPiso, EditarLugar,
    EditarTipoLugar, EditarCategoria, EditarObjeto,
    EditarTipoObjeto, EditarObjetoLugar, EditarHistorico,
    EstructuraCompletaForm, ObjetoLugarFilaFormSet, 
)

from .models import (
    Sector, Ubicacion, Piso, Lugar, TipoLugar,
    CategoriaObjeto, Objeto, TipoObjeto,
    ObjetoLugar, HistoricoObjeto, TipoLugarObjetoTipico,
)

# -------------------
# AUTH
# -------------------   

@login_required
def descargar_excel_sectores(request):
    ubicaciones = (Ubicacion.objects.select_related("sector").order_by("sector__sector","ubicacion"))
    xlsx_bytes = build_excel_sectores(ubicaciones)

    response = HttpResponse(xlsx_bytes, content_type="application/vnd.openxmlformats-officedocument.""spreadsheetml.sheet")
    response["Content-Disposition"]= 'attachment; filename= "SECTORES.xlsx"'
    return response

@login_required
@transaction.atomic
def crear_estructura(request):
    if request.method == "POST":
        form = EstructuraCompletaForm(request.POST)
        objetos_formset = ObjetoLugarFilaFormSet(request.POST, prefix="obj")

        if form.is_valid() and objetos_formset.is_valid():
            cd = form.cleaned_data

            # -----------------------
            # 1) SECTOR
            # -----------------------
            sector = cd.get("sector_existente")
            sector_nuevo = (cd.get("sector_nuevo") or "").strip()
            if not sector and sector_nuevo:
                sector, _ = Sector.objects.get_or_create(sector=sector_nuevo)

            # -----------------------
            # 2) UBICACIÓN
            # -----------------------
            ubicacion = cd.get("ubicacion_existente")
            ubicacion_nueva = (cd.get("ubicacion_nueva") or "").strip()
            if not ubicacion and ubicacion_nueva:
                ubicacion, _ = Ubicacion.objects.get_or_create(
                    ubicacion=ubicacion_nueva,
                    sector=sector,
                )

            # -----------------------
            # 3) PISO
            # -----------------------
            piso = cd.get("piso_existente")
            piso_nuevo = cd.get("piso_nuevo")
            if not piso and piso_nuevo not in (None, ""):
                piso, _ = Piso.objects.get_or_create(
                    piso=piso_nuevo,
                    ubicacion=ubicacion,
                )

            # -----------------------
            # 4) TIPO DE LUGAR
            # -----------------------
            tipo_lugar = cd.get("tipo_lugar_existente")
            tipo_lugar_nuevo = (cd.get("tipo_lugar_nuevo") or "").strip()
            if not tipo_lugar and tipo_lugar_nuevo:
                tipo_lugar, _ = TipoLugar.objects.get_or_create(
                    tipo_de_lugar=tipo_lugar_nuevo
                )

            # -----------------------
            # 5) LUGAR
            # -----------------------
            nombre_lugar = cd["nombre_del_lugar"].strip()
            lugar = Lugar.objects.create(
                nombre_del_lugar=nombre_lugar,
                piso=piso,
                lugar_tipo_lugar=tipo_lugar,
            )

            # -----------------------
            # 6) OBJETOS DEL LUGAR
            # -----------------------
            for f in objetos_formset:
                if not f.cleaned_data:
                    continue
                if f.cleaned_data.get("__empty__"):
                    continue

                row = f.cleaned_data

                # --- Categoría ---
                categoria = row.get("categoria_existente")
                if not categoria:
                    nombre_cat = (row.get("categoria_nueva") or "").strip()
                    categoria, _ = CategoriaObjeto.objects.get_or_create(
                        nombre_de_categoria=nombre_cat
                    )

                # --- Objeto ---
                objeto = row.get("objeto_existente")
                if not objeto:
                    nombre_obj = (row.get("objeto_nuevo") or "").strip()
                    objeto, _ = Objeto.objects.get_or_create(
                        nombre_del_objeto=nombre_obj,
                        objeto_categoria=categoria,
                    )

                # --- Tipo de objeto ---
                tipo_obj = row.get("tipo_objeto_existente")
                if not tipo_obj:
                    marca = (row.get("marca") or "").strip()
                    material = (row.get("material") or "").strip()
                    tipo_obj, _ = TipoObjeto.objects.get_or_create(
                        objeto=objeto,
                        marca=marca,
                        material=material,
                    )

                cantidad = row.get("cantidad") or 0
                estado = row.get("estado") or "B"
                detalle = (row.get("detalle") or "").strip()

                ObjetoLugar.objects.create(
                    lugar=lugar,
                    tipo_de_objeto=tipo_obj,
                    cantidad=cantidad,
                    estado=estado,
                    detalle=detalle,
                )

            # Redirige al detalle del lugar recién creado
            return redirect("detalle_lugar", lugar_id=lugar.id)

    else:
        form = EstructuraCompletaForm()
        objetos_formset = ObjetoLugarFilaFormSet(prefix="obj")

    return render(
        request,
        "crear_estructura.html",  # cambia este nombre si tu template es otro
        {
            "form": form,
            "objetos_formset": objetos_formset,
        },
    )


def signup(request):
    if request.method == "GET":
        return render(request, "signup.html", {"form": UserCreationForm})
    if request.POST["password1"] != request.POST["password2"]:
        return render(
            request,
            "signup.html",
            {"form": UserCreationForm, "error": "Las contraseñas no coinciden"},
        )

    try:
        user = User.objects.create_user(
            username=request.POST["username"],
            password=request.POST["password1"],
        )
        user.save()
        login(request, user)
        return redirect("home")
    except Exception:
        return render(
            request,
            "signup.html",
            {"form": UserCreationForm, "error": "Usuario ya existe"},
        )


def signin(request):
    if request.method == "GET":
        return render(request, "signin.html", {"form": AuthenticationForm})

    user = authenticate(
        request,
        username=request.POST["username"],
        password=request.POST["password"],
    )
    if user is None:
        return render(
            request,
            "signin.html",
            {
                "form": AuthenticationForm,
                "error": "Nombre o contraseña incorrectos",
            },
        )

    login(request, user)
    return redirect("home")


@login_required
def signout(request):
    logout(request)
    return redirect("signin")


@login_required
def home(request):
    return render(request, "home.html")


# -------------------
# UTIL: DELETE CONFIRM
# -------------------

def _confirm_delete(request, obj, cancel_url_name, cancel_kwargs, success_url_name):
    if request.method == "POST":
        obj.delete()
        return redirect(success_url_name)

    cancel_url = reverse(cancel_url_name, kwargs=cancel_kwargs)
    return render(request, "confirm_delete.html", {"obj": obj, "cancel_url": cancel_url})


# -------------------
# SECTOR
# -------------------

@login_required
def lista_sectores(request):
    sectores = Sector.objects.all().order_by("sector")
    return render(request, "sector/sectores.html", {"sectores": sectores})


@login_required
def detalle_sector(request, sector_id):
    sector = get_object_or_404(Sector, pk=sector_id)
    ubicaciones = Ubicacion.objects.filter(sector=sector).order_by("ubicacion")
    return render(
        request,
        "sector/detalle_sector.html",
        {"sector": sector, "ubicaciones": ubicaciones},
    )


@login_required
def crear_sector(request):
    if request.method == "GET":
        return render(request, "sector/crear_sector.html", {"form": CrearSector()})
    form = CrearSector(request.POST)
    if form.is_valid():
        form.save()
        return redirect("lista_sectores")
    return render(request, "sector/crear_sector.html", {"form": form})


@login_required
def editar_sector(request, sector_id):
    sector = get_object_or_404(Sector, pk=sector_id)
    if request.method == "GET":
        return render(
            request,
            "sector/editar_sector.html",
            {"form": EditarSector(instance=sector), "sector": sector},
        )

    form = EditarSector(request.POST, instance=sector)
    if form.is_valid():
        form.save()
        return redirect("detalle_sector", sector_id=sector.id)
    return render(
        request,
        "sector/editar_sector.html",
        {"form": form, "sector": sector},
    )


@login_required
def borrar_sector(request, sector_id):
    sector = get_object_or_404(Sector, pk=sector_id)
    return _confirm_delete(
        request, sector, "detalle_sector", {"sector_id": sector.id}, "lista_sectores"
    )


# -------------------
# UBICACION
# -------------------

@login_required
def lista_ubicaciones(request):
    # id de sector recibido por GET ?sector=3
    sector_id = request.GET.get("sector", "").strip()

    # query base
    ubicaciones_qs = Ubicacion.objects.select_related("sector").all()

    # si viene sector, filtramos
    if sector_id:
        try:
            ubicaciones_qs = ubicaciones_qs.filter(sector_id=int(sector_id))
        except ValueError:
            # si viene algo raro, ignoramos el filtro
            sector_id = ""

    ubicaciones = ubicaciones_qs.order_by("ubicacion")

    # para armar el combo
    sectores = Sector.objects.all().order_by("sector")

    return render(
        request,
        "ubicacion/ubicaciones.html",
        {
            "ubicaciones": ubicaciones,
            "sectores": sectores,
            "sector_actual": sector_id,  # lo usamos para marcar el option seleccionado
        },
    )



@login_required
def detalle_ubicacion(request, ubicacion_id):
    ubicacion = get_object_or_404(Ubicacion, pk=ubicacion_id)
    pisos = Piso.objects.filter(ubicacion=ubicacion).order_by("piso")
    return render(
        request,
        "ubicacion/detalle_ubicacion.html",
        {"ubicacion": ubicacion, "pisos": pisos},
    )


@login_required
def crear_ubicacion(request):
    if request.method == "GET":
        return render(request, "ubicacion/crear_ubicacion.html", {"form": CrearUbicacion()})
    form = CrearUbicacion(request.POST)
    if form.is_valid():
        ubicacion = form.save()
        return redirect("detalle_sector", sector_id=ubicacion.sector_id)
    return render(request, "ubicacion/crear_ubicacion.html", {"form": form})


@login_required
def editar_ubicacion(request, ubicacion_id):
    ubicacion = get_object_or_404(Ubicacion, pk=ubicacion_id)
    if request.method == "GET":
        return render(
            request,
            "ubicacion/editar_ubicacion.html",
            {"form": EditarUbicacion(instance=ubicacion), "ubicacion": ubicacion},
        )

    form = EditarUbicacion(request.POST, instance=ubicacion)
    if form.is_valid():
        form.save()
        return redirect("detalle_ubicacion", ubicacion_id=ubicacion.id)
    return render(
        request,
        "ubicacion/editar_ubicacion.html",
        {"form": form, "ubicacion": ubicacion},
    )


@login_required
def borrar_ubicacion(request, ubicacion_id):
    ubicacion = get_object_or_404(Ubicacion, pk=ubicacion_id)
    return _confirm_delete(
        request,
        ubicacion,
        "detalle_ubicacion",
        {"ubicacion_id": ubicacion.id},
        "lista_ubicaciones",
    )


# -------------------
# PISO
# -------------------

@login_required
def lista_pisos(request):
    # ?ubicacion=ID que llega por GET
    ubicacion_id = request.GET.get("ubicacion", "").strip()

    # queryset base
    pisos_qs = Piso.objects.select_related("ubicacion", "ubicacion__sector").all()

    # si viene ubicación, filtramos por esa ubicación
    if ubicacion_id:
        try:
            pisos_qs = pisos_qs.filter(ubicacion_id=int(ubicacion_id))
        except ValueError:
            ubicacion_id = ""  # si viene algo raro, ignoramos el filtro

    pisos = pisos_qs.order_by("ubicacion__ubicacion", "piso")

    # para llenar el combo de ubicaciones
    ubicaciones = Ubicacion.objects.select_related("sector").all().order_by("ubicacion")

    return render(
        request,
        "piso/pisos.html",  # deja aquí la ruta que ya usas
        {
            "pisos": pisos,
            "ubicaciones": ubicaciones,
            "ubicacion_actual": ubicacion_id,
        },
    )



@login_required
def detalle_piso(request, piso_id):
    piso = get_object_or_404(Piso, pk=piso_id)
    lugares = Lugar.objects.filter(piso=piso).order_by("nombre_del_lugar")
    return render(
        request,
        "piso/detalle_piso.html",
        {"piso": piso, "lugares": lugares},
    )


@login_required
def crear_piso(request):
    if request.method == "GET":
        return render(request, "piso/crear_piso.html", {"form": CrearPiso()})
    form = CrearPiso(request.POST)
    if form.is_valid():
        piso = form.save()
        return redirect("detalle_ubicacion", ubicacion_id=piso.ubicacion_id)
    return render(request, "piso/crear_piso.html", {"form": form})


@login_required
def editar_piso(request, piso_id):
    piso = get_object_or_404(Piso, pk=piso_id)
    cancel_url = reverse("detalle_piso", kwargs={"piso_id": piso.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar piso",
                "form": EditarPiso(instance=piso),
                "cancel_url": cancel_url,
            },
        )

    form = EditarPiso(request.POST, instance=piso)
    if form.is_valid():
        form.save()
        return redirect("detalle_piso", piso_id=piso.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar piso",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_piso(request, piso_id):
    piso = get_object_or_404(Piso, pk=piso_id)
    return _confirm_delete(
        request, piso, "detalle_piso", {"piso_id": piso.id}, "lista_pisos"
    )


# -------------------
# LUGAR
# -------------------

@login_required
def lista_lugares(request):
    ubicacion_id = request.GET.get("ubicacion", "").strip()
    piso_id = request.GET.get("piso", "").strip()

    # queryset base
    lugares_qs = Lugar.objects.select_related(
        "piso",
        "piso__ubicacion",
        "piso__ubicacion__sector",
    ).all()

    # filtro por ubicación
    if ubicacion_id:
        try:
            u_id = int(ubicacion_id)
            lugares_qs = lugares_qs.filter(piso__ubicacion_id=u_id)
        except ValueError:
            ubicacion_id = ""

    # filtro por piso
    if piso_id:
        try:
            p_id = int(piso_id)
            lugares_qs = lugares_qs.filter(piso_id=p_id)
        except ValueError:
            piso_id = ""

    lugares = lugares_qs.order_by(
        "piso__ubicacion__ubicacion",
        "piso__piso",
        "nombre_del_lugar",
    )

    # combos
    ubicaciones = Ubicacion.objects.select_related("sector").all().order_by("ubicacion")
    # OJO: aquí mandamos **todos** los pisos; el JS se encarga de filtrarlos en el combo
    pisos = Piso.objects.select_related("ubicacion").all().order_by(
        "ubicacion__ubicacion",
        "piso",
    )

    return render(
        request,
        "lugar/lugares.html",
        {
            "lugares": lugares,
            "ubicaciones": ubicaciones,
            "pisos": pisos,
            "ubicacion_actual": ubicacion_id,
            "piso_actual": piso_id,
        },
    )




@login_required
def detalle_lugar(request, lugar_id):
    lugar = get_object_or_404(Lugar, pk=lugar_id)
    objetos = (
        ObjetoLugar.objects.select_related("tipo_de_objeto", "tipo_de_objeto__objeto")
        .filter(lugar=lugar)
        .order_by("-fecha")
    )
    return render(
        request,
        "lugar/detalle_lugar.html",
        {"lugar": lugar, "objetos": objetos},
    )


@login_required
def crear_lugar(request):
    if request.method == "GET":
        return render(request, "lugar/crear_lugar.html", {"form": CrearLugar()})
    form = CrearLugar(request.POST)
    if form.is_valid():
        lugar = form.save()
        return redirect("detalle_piso", piso_id=lugar.piso_id)
    return render(request, "lugar/crear_lugar.html", {"form": form})


@login_required
def editar_lugar(request, lugar_id):
    lugar = get_object_or_404(Lugar, pk=lugar_id)
    cancel_url = reverse("detalle_lugar", kwargs={"lugar_id": lugar.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar lugar",
                "form": EditarLugar(instance=lugar),
                "cancel_url": cancel_url,
            },
        )

    form = EditarLugar(request.POST, instance=lugar)
    if form.is_valid():
        form.save()
        return redirect("detalle_lugar", lugar_id=lugar.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar lugar",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_lugar(request, lugar_id):
    lugar = get_object_or_404(Lugar, pk=lugar_id)
    return _confirm_delete(
        request, lugar, "detalle_lugar", {"lugar_id": lugar.id}, "lista_lugares"
    )


# -------------------
# OBJETO DEL LUGAR
# -------------------

@login_required
def lista_objetos_lugar(request):
    lugar_id = request.GET.get("lugar", "").strip()
    objeto_id = request.GET.get("objeto", "").strip()
    tipo_id = request.GET.get("tipo", "").strip()
    estado_val = request.GET.get("estado", "").strip()

    qs = ObjetoLugar.objects.select_related(
        "lugar",
        "lugar__piso",
        "lugar__piso__ubicacion",
        "lugar__piso__ubicacion__sector",
        "tipo_de_objeto",
        "tipo_de_objeto__objeto",
        "tipo_de_objeto__objeto__objeto_categoria",
    ).all()

    # Filtros
    if lugar_id:
        try:
            qs = qs.filter(lugar_id=int(lugar_id))
        except ValueError:
            lugar_id = ""

    if objeto_id:
        try:
            qs = qs.filter(tipo_de_objeto__objeto_id=int(objeto_id))
        except ValueError:
            objeto_id = ""

    if tipo_id:
        try:
            qs = qs.filter(tipo_de_objeto_id=int(tipo_id))
        except ValueError:
            tipo_id = ""

    if estado_val:
        qs = qs.filter(estado=estado_val)

    objetos_lugar = qs.order_by(
        "lugar__piso__ubicacion__ubicacion",
        "lugar__piso__piso",
        "lugar__nombre_del_lugar",
        "tipo_de_objeto__objeto__nombre_del_objeto",
    )

    # Datos para los combos
    lugares = (
        Lugar.objects.select_related(
            "piso",
            "piso__ubicacion",
            "piso__ubicacion__sector",
        )
        .all()
        .order_by(
            "piso__ubicacion__ubicacion",
            "piso__piso",
            "nombre_del_lugar",
        )
    )

    objetos = (
        Objeto.objects.select_related("objeto_categoria")
        .all()
        .order_by("objeto_categoria__nombre_de_categoria", "nombre_del_objeto")
    )

    tipos = (
        TipoObjeto.objects.select_related("objeto", "objeto__objeto_categoria")
        .all()
        .order_by("objeto__nombre_del_objeto", "marca", "material")
    )

    # choices del modelo (por ejemplo [("B", "Bueno"), ...])
    estados = ObjetoLugar.ESTADO

    return render(
        request,
        "objeto_lugar/objetos_lugar.html",  # <-- cambia la ruta si tu HTML está en otro lado
        {
            "objetos": objetos_lugar,
            "lugares": lugares,
            "objetos_catalogo": objetos,
            "tipos": tipos,
            "estados": estados,
            "lugar_actual": lugar_id,
            "objeto_actual": objeto_id,
            "tipo_actual": tipo_id,
            "estado_actual": estado_val,
        },
    )


@login_required
def detalle_objeto_lugar(request, objeto_lugar_id):
    obj = get_object_or_404(ObjetoLugar, pk=objeto_lugar_id)
    historicos = (
        HistoricoObjeto.objects
        .filter(objeto_del_lugar=obj)
        .order_by("-fecha_anterior")
    )
    return render(
        request,
        "objeto_lugar/detalle_objeto_lugar.html",
        {"objeto_lugar": obj, "historicos": historicos},
    )


@login_required
def crear_objeto_lugar(request, lugar_id):
    lugar = get_object_or_404(Lugar, pk=lugar_id)

    if request.method == "GET":
        return render(
            request,
            "objeto_lugar/crear_objeto_lugar.html",
            {"form": CrearObjetoLugar(), "lugar": lugar},
        )

    form = CrearObjetoLugar(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.lugar = lugar
        obj.save()
        return redirect("detalle_lugar", lugar_id=lugar.id)

    return render(
        request,
        "objeto_lugar/crear_objeto_lugar.html",
        {"form": form, "lugar": lugar},
    )


@login_required
def editar_objeto_lugar(request, objeto_lugar_id):
    objeto_lugar = get_object_or_404(ObjetoLugar, pk=objeto_lugar_id)
    cancel_url = reverse(
        "detalle_objeto_lugar",
        kwargs={"objeto_lugar_id": objeto_lugar.id},
    )

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar objeto del lugar",
                "form": EditarObjetoLugar(instance=objeto_lugar),
                "cancel_url": cancel_url,
            },
        )

    form = EditarObjetoLugar(request.POST, instance=objeto_lugar)
    if form.is_valid():
        form.save()
        return redirect("detalle_objeto_lugar", objeto_lugar_id=objeto_lugar.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar objeto del lugar",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_objeto_lugar(request, objeto_lugar_id):
    obj = get_object_or_404(ObjetoLugar, pk=objeto_lugar_id)
    return _confirm_delete(
        request,
        obj,
        "detalle_lugar",
        {"lugar_id": obj.lugar_id},
        "lista_objetos_lugar",
    )

# -------------------
# TIPO LUGAR
# -------------------

@login_required
def lista_tipos_lugar(request):
    tipos = TipoLugar.objects.all().order_by("tipo_de_lugar")
    return render(request, "tipo_lugar/tipos_lugar.html", {"tipos": tipos})


@login_required
def detalle_tipo_lugar(request, tipo_lugar_id):

    tipo = get_object_or_404(TipoLugar, pk=tipo_lugar_id)

    if request.method == "POST":
        ids = request.POST.getlist("tipicos")

        # normalizamos a ints y evitamos basura
        nuevos_ids = []
        for x in ids:
            try:
                nuevos_ids.append(int(x))
            except (TypeError, ValueError):
                pass

        with transaction.atomic():
            TipoLugarObjetoTipico.objects.filter(tipo_lugar=tipo).delete()
            TipoLugarObjetoTipico.objects.bulk_create(
                [
                    TipoLugarObjetoTipico(
                        tipo_lugar=tipo,
                        tipo_objeto_id=tipo_objeto_id,
                        activo=True,
                        orden=i,
                    )
                    for i, tipo_objeto_id in enumerate(nuevos_ids)
                ]
            )

        return redirect("detalle_tipo_lugar", tipo_lugar_id=tipo.id)

    lugares = Lugar.objects.filter(lugar_tipo_lugar=tipo).order_by("nombre_del_lugar")

    tipicos_qs = (
        TipoLugarObjetoTipico.objects.filter(tipo_lugar=tipo, activo=True)
        .select_related("tipo_objeto__objeto__objeto_categoria")
        .order_by(
            "orden",
            "tipo_objeto__objeto__objeto_categoria__nombre_de_categoria",
            "tipo_objeto__objeto__nombre_del_objeto",
            "tipo_objeto__marca",
            "tipo_objeto__material",
        )
    )
    tipicos_ids = list(tipicos_qs.values_list("tipo_objeto_id", flat=True))

    tipos_objeto = (
        TipoObjeto.objects.select_related("objeto__objeto_categoria")
        .all()
        .order_by(
            "objeto__objeto_categoria__nombre_de_categoria",
            "objeto__nombre_del_objeto",
            "marca",
            "material",
        )
    )

    return render(
        request,
        "tipo_lugar/detalle_tipo_lugar.html",
        {
            "tipo": tipo,
            "lugares": lugares,
            "tipicos": tipicos_qs,
            "tipicos_ids": tipicos_ids,
            "tipos_objeto": tipos_objeto,
        },
    )


@login_required
def crear_tipo_lugar(request):
    if request.method == "GET":
        return render(request, "tipo_lugar/crear_tipo_lugar.html", {"form": CrearTipoLugar()})
    form = CrearTipoLugar(request.POST)
    if form.is_valid():
        form.save()
        return redirect("lista_tipos_lugar")
    return render(request, "tipo_lugar/crear_tipo_lugar.html", {"form": form})


@login_required
def editar_tipo_lugar(request, tipo_lugar_id):
    tipo = get_object_or_404(TipoLugar, pk=tipo_lugar_id)
    cancel_url = reverse("detalle_tipo_lugar", kwargs={"tipo_lugar_id": tipo.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar tipo de lugar",
                "form": EditarTipoLugar(instance=tipo),
                "cancel_url": cancel_url,
            },
        )

    form = EditarTipoLugar(request.POST, instance=tipo)
    if form.is_valid():
        form.save()
        return redirect("detalle_tipo_lugar", tipo_lugar_id=tipo.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar tipo de lugar",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_tipo_lugar(request, tipo_lugar_id):
    tipo = get_object_or_404(TipoLugar, pk=tipo_lugar_id)
    return _confirm_delete(
        request,
        tipo,
        "detalle_tipo_lugar",
        {"tipo_lugar_id": tipo.id},
        "lista_tipos_lugar",
    )


# -------------------
# CATEGORIA / OBJETO / TIPO OBJETO
# -------------------

@login_required
def lista_categorias(request):
    categorias = CategoriaObjeto.objects.all().order_by("nombre_de_categoria")
    return render(request, "categoria/categorias.html", {"categorias": categorias})


@login_required
def detalle_categoria(request, categoria_id):
    categoria = get_object_or_404(CategoriaObjeto, pk=categoria_id)
    objetos = Objeto.objects.filter(objeto_categoria_id=categoria_id).order_by("nombre_del_objeto")
    return render(
        request,
        "categoria/detalle_categoria.html",
        {"categoria": categoria, "objetos": objetos},
    )


@login_required
def crear_categoria_objeto(request):
    if request.method == "GET":
        return render(
            request,
            "categoria/crear_categoria_objeto.html",
            {"form": CrearCategoriaObjeto()},
        )
    form = CrearCategoriaObjeto(request.POST)
    if form.is_valid():
        form.save()
        return redirect("lista_categorias")
    return render(request, "categoria/crear_categoria_objeto.html", {"form": form})


@login_required
def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(CategoriaObjeto, pk=categoria_id)
    cancel_url = reverse("detalle_categoria", kwargs={"categoria_id": categoria.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar categoría",
                "form": EditarCategoria(instance=categoria),
                "cancel_url": cancel_url,
            },
        )

    form = EditarCategoria(request.POST, instance=categoria)
    if form.is_valid():
        form.save()
        return redirect("detalle_categoria", categoria_id=categoria.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar categoría",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_categoria(request, categoria_id):
    categoria = get_object_or_404(CategoriaObjeto, pk=categoria_id)
    return _confirm_delete(
        request,
        categoria,
        "detalle_categoria",
        {"categoria_id": categoria.id},
        "lista_categorias",
    )


@login_required
def lista_objetos(request):
    # ?categoria=ID que llega por GET
    categoria_id = request.GET.get("categoria", "").strip()

    # queryset base
    objetos_qs = Objeto.objects.select_related("objeto_categoria").all()

    # si viene categoría, filtramos
    if categoria_id:
        try:
            objetos_qs = objetos_qs.filter(objeto_categoria_id=int(categoria_id))
        except ValueError:
            categoria_id = ""  # si viene algo raro, ignoramos el filtro

    objetos = objetos_qs.order_by(
        "objeto_categoria__nombre_de_categoria",
        "nombre_del_objeto",
    )

    # para el combo de categorías
    categorias = CategoriaObjeto.objects.all().order_by("nombre_de_categoria")

    return render(
        request,
        "objeto/objetos.html",   # deja aquí la ruta real de tu template
        {
            "objetos": objetos,
            "categorias": categorias,
            "categoria_actual": categoria_id,
        },
    )


@login_required
def detalle_objeto(request, objeto_id):
    objeto = get_object_or_404(Objeto, pk=objeto_id)
    tipos = TipoObjeto.objects.filter(objeto=objeto).order_by("marca", "material")
    return render(
        request,
        "objeto/detalle_objeto.html",
        {"objeto": objeto, "tipos": tipos},
    )


@login_required
def crear_objeto(request):
    if request.method == "GET":
        return render(request, "objeto/crear_objeto.html", {"form": CrearObjeto()})
    form = CrearObjeto(request.POST)
    if form.is_valid():
        form.save()
        return redirect("lista_objetos")
    return render(request, "objeto/crear_objeto.html", {"form": form})


@login_required
def editar_objeto(request, objeto_id):
    objeto = get_object_or_404(Objeto, pk=objeto_id)
    cancel_url = reverse("detalle_objeto", kwargs={"objeto_id": objeto.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar objeto",
                "form": EditarObjeto(instance=objeto),
                "cancel_url": cancel_url,
            },
        )

    form = EditarObjeto(request.POST, instance=objeto)
    if form.is_valid():
        form.save()
        return redirect("detalle_objeto", objeto_id=objeto.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar objeto",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_objeto(request, objeto_id):
    objeto = get_object_or_404(Objeto, pk=objeto_id)
    return _confirm_delete(
        request,
        objeto,
        "detalle_objeto",
        {"objeto_id": objeto.id},
        "lista_objetos",
    )


@login_required
def lista_tipos_objeto(request):
    # ?categoria=ID & ?objeto=ID
    categoria_id = request.GET.get("categoria", "").strip()
    objeto_id = request.GET.get("objeto", "").strip()

    # queryset base
    tipos_qs = TipoObjeto.objects.select_related(
        "objeto",
        "objeto__objeto_categoria",
    ).all()

    # filtro por categoría (a través del objeto)
    if categoria_id:
        try:
            c_id = int(categoria_id)
            tipos_qs = tipos_qs.filter(objeto__objeto_categoria_id=c_id)
        except ValueError:
            categoria_id = ""

    # filtro por objeto
    if objeto_id:
        try:
            o_id = int(objeto_id)
            tipos_qs = tipos_qs.filter(objeto_id=o_id)
        except ValueError:
            objeto_id = ""

    tipos_objeto = tipos_qs.order_by(
        "objeto__objeto_categoria__nombre_de_categoria",
        "objeto__nombre_del_objeto",
        "marca",
        "material",
    )

    # ===== combos =====
    categorias = CategoriaObjeto.objects.all().order_by("nombre_de_categoria")

    # mandamos TODOS los objetos, el JS se encarga de mostrar sólo los de la categoría elegida
    objetos = Objeto.objects.select_related("objeto_categoria").all().order_by(
        "objeto_categoria__nombre_de_categoria",
        "nombre_del_objeto",
    )

    return render(
        request,
        "tipo_objeto/tipos_objeto.html",  # ajusta la ruta si tu template está en otro lado
        {
            "tipos_objeto": tipos_objeto,
            "categorias": categorias,
            "objetos": objetos,
            "categoria_actual": categoria_id,
            "objeto_actual": objeto_id,
        },
    )



@login_required
def detalle_tipo_objeto(request, tipo_objeto_id):
    tipo = get_object_or_404(TipoObjeto, pk=tipo_objeto_id)
    usados = (
        ObjetoLugar.objects.filter(tipo_de_objeto=tipo)
        .select_related("lugar")
        .order_by("-fecha")
    )
    return render(
        request,
        "tipo_objeto/detalle_tipo_objeto.html",
        {"tipo": tipo, "usados": usados},
    )


@login_required
def crear_tipo_objeto(request):
    if request.method == "GET":
        return render(request, "tipo_objeto/crear_tipo_objeto.html", {"form": CrearTipoObjeto()})
    form = CrearTipoObjeto(request.POST)
    if form.is_valid():
        form.save()
        return redirect("lista_tipos_objeto")
    return render(request, "tipo_objeto/crear_tipo_objeto.html", {"form": form})


@login_required
def editar_tipo_objeto(request, tipo_objeto_id):
    tipo = get_object_or_404(TipoObjeto, pk=tipo_objeto_id)
    cancel_url = reverse("detalle_tipo_objeto", kwargs={"tipo_objeto_id": tipo.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar tipo de objeto",
                "form": EditarTipoObjeto(instance=tipo),
                "cancel_url": cancel_url,
            },
        )

    form = EditarTipoObjeto(request.POST, instance=tipo)
    if form.is_valid():
        form.save()
        return redirect("detalle_tipo_objeto", tipo_objeto_id=tipo.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar tipo de objeto",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_tipo_objeto(request, tipo_objeto_id):
    tipo = get_object_or_404(TipoObjeto, pk=tipo_objeto_id)
    return _confirm_delete(
        request,
        tipo,
        "detalle_tipo_objeto",
        {"tipo_objeto_id": tipo.id},
        "lista_tipos_objeto",
    )


# -------------------
# HISTORICO
# -------------------

@login_required
def lista_historicos(request):
    lugar_id = request.GET.get("lugar", "").strip()
    objeto_id = request.GET.get("objeto", "").strip()
    tipo_id = request.GET.get("tipo", "").strip()
    estado_val = request.GET.get("estado", "").strip()

    qs = HistoricoObjeto.objects.select_related(
        "objeto_del_lugar",
        "objeto_del_lugar__lugar",
        "objeto_del_lugar__lugar__piso",
        "objeto_del_lugar__lugar__piso__ubicacion",
        "objeto_del_lugar__lugar__piso__ubicacion__sector",
        "objeto_del_lugar__tipo_de_objeto",
        "objeto_del_lugar__tipo_de_objeto__objeto",
        "objeto_del_lugar__tipo_de_objeto__objeto__objeto_categoria",
    ).all()

    # ---- Filtros ----
    if lugar_id:
        try:
            qs = qs.filter(objeto_del_lugar__lugar_id=int(lugar_id))
        except ValueError:
            lugar_id = ""

    if objeto_id:
        try:
            qs = qs.filter(objeto_del_lugar__tipo_de_objeto__objeto_id=int(objeto_id))
        except ValueError:
            objeto_id = ""

    if tipo_id:
        try:
            qs = qs.filter(objeto_del_lugar__tipo_de_objeto_id=int(tipo_id))
        except ValueError:
            tipo_id = ""

    if estado_val:
        qs = qs.filter(estado_anterior=estado_val)

    historicos = qs.order_by(
        "-fecha_anterior",
        "objeto_del_lugar__lugar__piso__ubicacion__ubicacion",
        "objeto_del_lugar__lugar__piso__piso",
        "objeto_del_lugar__lugar__nombre_del_lugar",
    )

    # ---- datos para los combos ----
    lugares = (
        Lugar.objects.select_related(
            "piso",
            "piso__ubicacion",
            "piso__ubicacion__sector",
        )
        .all()
        .order_by(
            "piso__ubicacion__ubicacion",
            "piso__piso",
            "nombre_del_lugar",
        )
    )

    objetos = (
        Objeto.objects.select_related("objeto_categoria")
        .all()
        .order_by("objeto_categoria__nombre_de_categoria", "nombre_del_objeto")
    )

    tipos = (
        TipoObjeto.objects.select_related("objeto", "objeto__objeto_categoria")
        .all()
        .order_by("objeto__nombre_del_objeto", "marca", "material")
    )

    # choices del campo estado_anterior
    estados = HistoricoObjeto._meta.get_field("estado_anterior").choices

    return render(
        request,
        "historico/historicos.html",   # pon aquí la ruta real de tu template
        {
            "historicos": historicos,
            "lugares": lugares,
            "objetos_catalogo": objetos,
            "tipos": tipos,
            "estados": estados,
            "lugar_actual": lugar_id,
            "objeto_actual": objeto_id,
            "tipo_actual": tipo_id,
            "estado_actual": estado_val,
        },
    )


@login_required
def detalle_historico(request, historico_id):
    historico = get_object_or_404(HistoricoObjeto, pk=historico_id)
    return render(request, "historico/detalle_historico.html", {"historico": historico})


@login_required
def crear_historico(request, objeto_lugar_id):
    objeto_lugar = get_object_or_404(ObjetoLugar, pk=objeto_lugar_id)

    if request.method == "GET":
        form = CrearHistorico(
            initial={
                "cantidad_anterior": objeto_lugar.cantidad,
                "estado_anterior": objeto_lugar.estado,
                "detalle_anterior": objeto_lugar.detalle,
                "fecha_anterior": objeto_lugar.fecha,
                "objeto_del_lugar": objeto_lugar.id,
            }
        )
        return render(
            request,
            "historico/crear_historico.html",
            {"form": form, "objeto_lugar": objeto_lugar},
        )

    form = CrearHistorico(request.POST)
    if form.is_valid():
        h = form.save(commit=False)
        h.objeto_del_lugar = objeto_lugar
        h.save()
        return redirect("detalle_objeto_lugar", objeto_lugar_id=objeto_lugar.id)

    return render(
        request,
        "historico/crear_historico.html",
        {"form": form, "objeto_lugar": objeto_lugar},
    )


@login_required
def editar_historico(request, historico_id):
    historico = get_object_or_404(HistoricoObjeto, pk=historico_id)
    cancel_url = reverse("detalle_historico", kwargs={"historico_id": historico.id})

    if request.method == "GET":
        return render(
            request,
            "editar_generico.html",
            {
                "titulo": "Editar histórico",
                "form": EditarHistorico(instance=historico),
                "cancel_url": cancel_url,
            },
        )

    form = EditarHistorico(request.POST, instance=historico)
    if form.is_valid():
        form.save()
        return redirect("detalle_historico", historico_id=historico.id)

    return render(
        request,
        "editar_generico.html",
        {
            "titulo": "Editar histórico",
            "form": form,
            "cancel_url": cancel_url,
        },
    )


@login_required
def borrar_historico(request, historico_id):
    historico = get_object_or_404(HistoricoObjeto, pk=historico_id)
    return _confirm_delete(
        request,
        historico,
        "detalle_historico",
        {"historico_id": historico.id},
        "lista_historicos",
    )


# -------------------
# RESUMEN
# -------------------

def _add_percentages(rows):
    for r in rows:
        total = r.get("total") or 0
        b = r.get("buenas") or 0
        p = r.get("pendientes") or 0
        m = r.get("malas") or 0

        if total == 0:
            r["pct_buenas"] = r["pct_pendientes"] = r["pct_malas"] = 0
        else:
            r["pct_buenas"] = round(b * 100 / total, 1)
            r["pct_pendientes"] = round(p * 100 / total, 1)
            r["pct_malas"] = round(m * 100 / total, 1)
    return rows


def resumen_general(request):
    # ----------------------
    # 1) Leer filtros del GET
    # ----------------------
    sector_id = request.GET.get("sector") or None
    ubicacion_id = request.GET.get("ubicacion") or None
    piso_id = request.GET.get("piso") or None
    tipo_lugar_id = request.GET.get("tipo_lugar") or None
    categoria_id = request.GET.get("categoria") or None
    objeto_id = request.GET.get("objeto") or None
    tipo_objeto_id = request.GET.get("tipo_objeto") or None
    estado = request.GET.get("estado") or None
    marca = request.GET.get("marca") or None
    material = request.GET.get("material") or None

    # ----------------------
    # 2) Base de datos filtrada
    # ----------------------
    base_qs = ObjetoLugar.objects.select_related(
        "lugar",
        "lugar__piso",
        "lugar__piso__ubicacion",
        "lugar__piso__ubicacion__sector",
        "lugar__lugar_tipo_lugar",
        "tipo_de_objeto",
        "tipo_de_objeto__objeto",
        "tipo_de_objeto__objeto__objeto_categoria",
    )

    if sector_id:
        base_qs = base_qs.filter(lugar__piso__ubicacion__sector_id=sector_id)
    if ubicacion_id:
        base_qs = base_qs.filter(lugar__piso__ubicacion_id=ubicacion_id)
    if piso_id:
        base_qs = base_qs.filter(lugar__piso_id=piso_id)
    if tipo_lugar_id:
        base_qs = base_qs.filter(lugar__lugar_tipo_lugar_id=tipo_lugar_id)
    if categoria_id:
        base_qs = base_qs.filter(
            tipo_de_objeto__objeto__objeto_categoria_id=categoria_id
        )
    if objeto_id:
        base_qs = base_qs.filter(tipo_de_objeto__objeto_id=objeto_id)
    if tipo_objeto_id:
        base_qs = base_qs.filter(tipo_de_objeto_id=tipo_objeto_id)
    if estado:
        base_qs = base_qs.filter(estado=estado)
    if marca:
        base_qs = base_qs.filter(tipo_de_objeto__marca=marca)
    if material:
        base_qs = base_qs.filter(tipo_de_objeto__material=material)

    # ----------------------
    # 3) Resumen por sector
    # ----------------------
    qs_sector = (
        base_qs.values(
            "lugar__piso__ubicacion__sector__id",
            "lugar__piso__ubicacion__sector__sector",
        )
        .annotate(
            total=Sum("cantidad"),
            buenas=Sum("cantidad", filter=Q(estado="B")),
            pendientes=Sum("cantidad", filter=Q(estado="P")),
            malas=Sum("cantidad", filter=Q(estado="M")),
        )
        .order_by("lugar__piso__ubicacion__sector__sector")
    )
    resumen_sector = list(qs_sector)
    _add_percentages(resumen_sector)

    # ----------------------
    # 4) Resumen por ubicación
    # ----------------------
    qs_ubic = (
        base_qs.values(
            "lugar__piso__ubicacion__id",
            "lugar__piso__ubicacion__ubicacion",
            "lugar__piso__ubicacion__sector__sector",
        )
        .annotate(
            total=Sum("cantidad"),
            buenas=Sum("cantidad", filter=Q(estado="B")),
            pendientes=Sum("cantidad", filter=Q(estado="P")),
            malas=Sum("cantidad", filter=Q(estado="M")),
        )
        .order_by(
            "lugar__piso__ubicacion__sector__sector",
            "lugar__piso__ubicacion__ubicacion",
        )
    )
    resumen_ubic = list(qs_ubic)
    _add_percentages(resumen_ubic)

    # ----------------------
    # 5) Resumen por objeto (objeto, no tipo)
    # ----------------------
    qs_obj = (
        base_qs.values(
            "tipo_de_objeto__objeto__id",
            "tipo_de_objeto__objeto__nombre_del_objeto",
        )
        .annotate(
            total=Sum("cantidad"),
            buenas=Sum("cantidad", filter=Q(estado="B")),
            pendientes=Sum("cantidad", filter=Q(estado="P")),
            malas=Sum("cantidad", filter=Q(estado="M")),
        )
        .order_by("tipo_de_objeto__objeto__nombre_del_objeto")
    )
    resumen_obj = list(qs_obj)
    _add_percentages(resumen_obj)

    # Objetos en estado malo, para el detalle por objeto
    malos_qs = (
        base_qs.filter(estado="M")
        .select_related(
            "lugar__piso__ubicacion__sector",
            "lugar__piso__ubicacion",
            "lugar__piso",
            "lugar",
            "tipo_de_objeto__objeto",
        )
        .order_by(
            "tipo_de_objeto__objeto__nombre_del_objeto",
            "lugar__piso__ubicacion__sector__sector",
            "lugar__piso__ubicacion__ubicacion",
            "lugar__piso__piso",
            "lugar__nombre_del_lugar",
        )
    )

    malos_por_objeto = {}
    for ol in malos_qs:
        oid = ol.tipo_de_objeto.objeto_id
        malos_por_objeto.setdefault(oid, []).append(ol)

    resumen_objetos = []
    for r in resumen_obj:
        oid = r["tipo_de_objeto__objeto__id"]
        resumen_objetos.append(
            {
                "id": oid,
                "nombre": r["tipo_de_objeto__objeto__nombre_del_objeto"],
                "total": r["total"] or 0,
                "buenas": r["buenas"] or 0,
                "pendientes": r["pendientes"] or 0,
                "malas": r["malas"] or 0,
                "pct_buenas": r["pct_buenas"],
                "pct_pendientes": r["pct_pendientes"],
                "pct_malas": r["pct_malas"],
                "malos": malos_por_objeto.get(oid, []),
            }
        )

    # ----------------------
    # 6) Datos para los combos de filtros
    # ----------------------
    sectores = Sector.objects.order_by("sector")
    ubicaciones = Ubicacion.objects.select_related("sector").order_by(
        "sector__sector", "ubicacion"
    )
    pisos = Piso.objects.select_related("ubicacion").order_by(
        "ubicacion__ubicacion", "piso"
    )
    tipos_lugar = TipoLugar.objects.order_by("tipo_de_lugar")
    categorias = CategoriaObjeto.objects.order_by("nombre_de_categoria")
    objetos_catalogo = Objeto.objects.select_related("objeto_categoria").order_by(
        "nombre_del_objeto"
    )
    tipos_objeto = TipoObjeto.objects.select_related("objeto").order_by(
        "objeto__nombre_del_objeto", "marca", "material"
    )

    # NUEVO: marcas y materiales únicos
    marcas = (
        TipoObjeto.objects.order_by("marca")
        .values_list("marca", flat=True)
        .distinct()
    )
    materiales = (
        TipoObjeto.objects.order_by("material")
        .values_list("material", flat=True)
        .distinct()
    )

    estados = ObjetoLugar.ESTADO

    contexto = {
        "resumen_sector": resumen_sector,
        "resumen_ubic": resumen_ubic,
        "resumen_objetos": resumen_objetos,
        # combos
        "sectores": sectores,
        "ubicaciones": ubicaciones,
        "pisos": pisos,
        "tipos_lugar": tipos_lugar,
        "categorias": categorias,
        "objetos_catalogo": objetos_catalogo,
        "tipos_objeto": tipos_objeto,
        "estados": estados,
        "marcas": marcas,
        "materiales": materiales,
        # valores seleccionados
        "sector_actual": sector_id or "",
        "ubicacion_actual": ubicacion_id or "",
        "piso_actual": piso_id or "",
        "tipo_lugar_actual": tipo_lugar_id or "",
        "categoria_actual": categoria_id or "",
        "objeto_actual": objeto_id or "",
        "tipo_objeto_actual": tipo_objeto_id or "",
        "estado_actual": estado or "",
        "marca_actual": marca or "",
        "material_actual": material or "",
    }

    return render(request, "resumen/resumen_general.html", contexto)


    # -------------------------
# AJAX: combos dependientes
# -------------------------

def ajax_ubicaciones_por_sector(request):
    """
    Devuelve las ubicaciones ligadas a un sector (para el combo de Ubicación).
    GET: ?sector_id=<id>
    """
    sector_id = request.GET.get("sector_id")
    from .models import Ubicacion  # import local para no romper nada

    qs = Ubicacion.objects.filter(sector_id=sector_id).order_by("ubicacion")
    data = [{"id": u.id, "nombre": u.ubicacion} for u in qs]
    return JsonResponse(data, safe=False)


def ajax_pisos_por_ubicacion(request):
    """
    Devuelve los pisos ligados a una ubicación (para el combo de Piso).
    GET: ?ubicacion_id=<id>
    """
    ubicacion_id = request.GET.get("ubicacion_id")
    from .models import Piso

    qs = Piso.objects.filter(ubicacion_id=ubicacion_id).order_by("piso")
    data = [{"id": p.id, "nombre": f"Piso {p.piso}"} for p in qs]
    return JsonResponse(data, safe=False)


def ajax_lugares_por_piso(request):
    """
    (Por si lo necesitas) Devuelve lugares ligados a un piso.
    GET: ?piso_id=<id>
    """
    piso_id = request.GET.get("piso_id")
    from .models import Lugar

    qs = Lugar.objects.filter(piso_id=piso_id).order_by("nombre_del_lugar")
    data = [{"id": l.id, "nombre": l.nombre_del_lugar} for l in qs]
    return JsonResponse(data, safe=False)


def ajax_objetos_por_categoria(request):
    """
    Devuelve los OBJETOS de una categoría (para el combo de Objeto).
    GET: ?categoria_id=<id>
    """
    categoria_id = request.GET.get("categoria_id")
    from .models import Objeto

    qs = Objeto.objects.filter(objeto_categoria_id=categoria_id).order_by(
        "nombre_del_objeto"
    )
    data = [{"id": o.id, "nombre": o.nombre_del_objeto} for o in qs]
    return JsonResponse(data, safe=False)


def ajax_tipos_por_objeto(request):
    """
    Devuelve los TIPOS de objeto (marca/material) ligados a un objeto.
    GET: ?objeto_id=<id>
    """
    objeto_id = request.GET.get("objeto_id")
    from .models import TipoObjeto

    qs = TipoObjeto.objects.filter(objeto_id=objeto_id).order_by("marca", "material")
    data = [
        {
            "id": t.id,
            "nombre": f"{t.marca} {t.material}",
        }
        for t in qs
    ]
    return JsonResponse(data, safe=False)

TIPICOS_POR_TIPO_LUGAR = {
    "Baño": {
        "Infraestructura": [
            "Paredes", "Piso", "Cielo", "Techo", "Luces" ,"Ventanas", "Puertas",
            "Conexión eléctrica", "Interruptores"
        ],
        "Sanitario": [
            "Tasas", "Urinario","Desagües","Papeleros","Lavamanos"
        ],
        "Decoración":[
            "Espejos",
        ],
        "Higiene":[
            "Jaboneras","Dispensadores de papel", "Dispensadores de jabón"
        ],
    },
    "Vestidor": {
        "Infraestructura": [
            "Paredes", "Piso", "Cielo", "Techo", "Luces" ,"Ventanas", "Puertas",
            "Conexión eléctrica", "Interruptores"
        ],
        "Mobiliario": [
            "Bancos", "Casilleros", "Percheros",
        ],
        "Sanitario":[
            "Duchas",
        ],
        "Higiene":[
            "Secadores de toalla","Dispensadores de jabón"
        ],
        "Climatización":[
            "Extractores","Estufas"
        ],
    },
    "Comedor": {
        "Infraestructura": [
            "Paredes", "Piso", "Cielo", "Techo", "Luces" ,"Ventanas", "Puertas",
            "Conexión eléctrica", "Interruptores"
        ],
        "Mobiliario":[
            "Mesas","Sillas","Muebles"
        ],
        "Electrodomésticos": [
            "Refrigerador","Microondas","Dispensador de agua","Televisor",
        ],
        "Sanitario":[
            "Lavaplatos","Papeleros"
        ],
        "Climatización":[
            "Aire acondicionado"
        ],
    },
    "Cafetería":{
        "Infraestructura": [
            "Paredes", "Piso", "Cielo", "Techo", "Luces" ,"Ventanas", "Puertas",
            "Conexión eléctrica", "Interruptores"
        ],
        "Mobiliario":[
            "Mesas","Sillas","Muebles"
        ],
        "Electrodomésticos":[
            "Cafetera","Refrigerador","Dispensador de agua"
        ],
        "Climatización":[
            "Aire acondicionado"
        ],
    },
    "Baño vestidor":{
        "Infraestructura": [
            "Paredes", "Piso", "Cielo", "Techo", "Luces" ,"Ventanas", "Puertas",
            "Conexión eléctrica", "Interruptores"
        ],
        "Sanitario": [
            "Tasas", "Urinario","Desagües","Lavamanos","Duchas","Papeleros"
        ],
        "Decoración":[
            "Espejos",
        ],
        "Higiene":[
            "Secadores de toalla", "Dispensadores de jabón"
        ],
        "Mobiliario":[
            "Bancas","Casilleros",
        ],
        "Climatización":[
            "Extractores"
        ],
    }
}


@require_GET
def objetos_tipicos_por_tipo_lugar(request, tipo_lugar_pk):

    tipo_lugar = get_object_or_404(TipoLugar, pk=tipo_lugar_pk)

    qs = (
        TipoLugarObjetoTipico.objects.filter(tipo_lugar=tipo_lugar, activo=True)
        .select_related("tipo_objeto__objeto__objeto_categoria")
        .order_by(
            "orden",
            "tipo_objeto__objeto__objeto_categoria__nombre_de_categoria",
            "tipo_objeto__objeto__nombre_del_objeto",
            "tipo_objeto__marca",
            "tipo_objeto__material",
        )
    )

    # Seed automático (1 sola vez) desde tu TIPICOS_POR_TIPO_LUGAR, y queda en DB
    if not qs.exists():
        tipicos = TIPICOS_POR_TIPO_LUGAR.get(tipo_lugar.tipo_de_lugar, {})

        if tipicos:
            orden = 0
            with transaction.atomic():
                for nombre_categoria, lista_objetos in tipicos.items():
                    categoria_obj, _ = CategoriaObjeto.objects.get_or_create(
                        nombre_de_categoria=nombre_categoria
                    )

                    for nombre_obj in lista_objetos:
                        obj, _ = Objeto.objects.get_or_create(
                            nombre_del_objeto=nombre_obj,
                            defaults={"objeto_categoria": categoria_obj},
                        )
                        # si ya existía pero con otra categoría, no lo tocamos
                        if obj.objeto_categoria_id != categoria_obj.id:
                            categoria_obj = obj.objeto_categoria

                        tipo_objeto, _ = TipoObjeto.objects.get_or_create(
                            objeto=obj,
                            marca="",
                            material="",
                        )

                        TipoLugarObjetoTipico.objects.get_or_create(
                            tipo_lugar=tipo_lugar,
                            tipo_objeto=tipo_objeto,
                            defaults={"activo": True, "orden": orden},
                        )
                        orden += 1

            qs = (
                TipoLugarObjetoTipico.objects.filter(tipo_lugar=tipo_lugar, activo=True)
                .select_related("tipo_objeto__objeto__objeto_categoria")
                .order_by(
                    "orden",
                    "tipo_objeto__objeto__objeto_categoria__nombre_de_categoria",
                    "tipo_objeto__objeto__nombre_del_objeto",
                    "tipo_objeto__marca",
                    "tipo_objeto__material",
                )
            )

    data = []
    for rel in qs:
        t = rel.tipo_objeto
        cat = t.objeto.objeto_categoria
        obj = t.objeto

        marca = (t.marca or "").strip()
        material = (t.material or "").strip()
        extra = ""
        if marca or material:
            extra = f" ({marca} {material})".strip()

        data.append(
            {
                "categoria_id": cat.id,
                "objeto_id": obj.id,
                "tipo_objeto_id": t.id,
                "label": f"{cat.nombre_de_categoria} - {obj.nombre_del_objeto}{extra}",
            }
        )

    return JsonResponse(data, safe=False)
