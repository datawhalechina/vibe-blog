# Media Service Boundary

Image and video capabilities live under one package:

```text
backend/services/media/
├── image_service.py
├── image_styles/
├── sora2_service.py
├── video_sequence_service.py
└── video_service.py
```

Use the package API for image and video service lifecycle calls:

```python
from services.media import get_image_service, get_video_service
```

Specialized callers may import from explicit submodules such as
`services.media.image_styles` or `services.media.video_sequence_service`.

## Compatibility

The previous `services.image_service`, `services.video_service`,
`services.video_sequence_service`, `services.sora2_service`, and
`services.image_styles` paths remain module aliases. This preserves singleton
state, class identity, and existing patch targets while downstream callers move
to the new package.
