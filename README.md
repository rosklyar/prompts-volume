# prompts-volume
This is the repo for the service which proposes prompts for certain business

## Tech stack
- Using python 3.12 and FastAPI for serving requests
- uv as dependency management and build tool, we also run code and tests through
- Docker for containerization
- PostgreSQL for serving state

## Repo structure
- All source code should be located in src/
- All tests should be run with pytest and located in tests/
- .Dockerfile and .env.example should be located in .

## Main functionality
### Return topics/keywords relevant for you and your industry
- GET /prompts/api/v1/topics?url=tryprofound.com

