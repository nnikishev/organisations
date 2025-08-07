from fastapi import Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from app.common import CRUD
from app.models import Organization
from app.schemas import OrganisationCreateUpdate, OrganisationSchema

router = InferringRouter()

API_KEY = "YOUR_STATIC_API_KEY"


def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return x_api_key


@cbv(router)
class OrganizationViews(CRUD):
    """
    CRUD и специализированные эндпоинты для справочника организаций.
    """

    model = Organization
    create_update_schema = OrganisationCreateUpdate

    @router.post(
        "/organizations/",
        response_model=OrganisationSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать организацию",
    )
    def create_organization(self, data: OrganisationCreateUpdate):
        organisation = super().create(data)
        return JSONResponse(
            jsonable_encoder(organisation), status_code=status.HTTP_201_CREATED
        )
