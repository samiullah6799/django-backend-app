from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from routing.services.planner import plan
from routing.services.resolver import LocationError
from routing.services.osrm import RouteError
from routing.services.optimizer import InfeasibleRoute


@api_view(["GET"])
def route_view(request):
    start = request.GET.get("start")
    finish = request.GET.get("finish")
    if not start or not finish:
        return Response({"error": "start and finish are required"}, status=400)
    try:
        return Response(plan(start, finish))
    except LocationError as e:
        return Response({"error": str(e)}, status=400)
    except InfeasibleRoute as e:
        return Response({"error": str(e)}, status=422)
    except RouteError as e:
        return Response({"error": str(e)}, status=503)

def map_view(request):
    return render(request, "routing/map.html")