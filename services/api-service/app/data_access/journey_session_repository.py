from fastcrud import FastCRUD

from app.models import JourneySession
from app.schemas.journey_session_schemas import JourneySessionCreate, JourneySessionUpdate, JourneySessionRead

# FastCRUD pattern - all CRUD operations built-in!
CRUDJourneySession = FastCRUD[JourneySession, JourneySessionCreate, JourneySessionUpdate, JourneySessionUpdate, JourneySessionUpdate, JourneySessionRead]
crud_journey_sessions = CRUDJourneySession(JourneySession)
