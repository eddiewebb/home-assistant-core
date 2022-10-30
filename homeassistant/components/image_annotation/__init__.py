"""Annotation Service allows custom text to be overlaid on image files."""

import logging
from typing import Final

from PIL import Image as PilImage, ImageDraw, ImageFont
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


DOMAIN = "image_annotation"
ACTION = "annotate"


ATTR_FILENAME: Final = "filename"
ATTR_ANNOTATION: Final = "annotation"


IMAGE_ANNOTATION_ANNOTATE: Final = {
    vol.Required(ATTR_FILENAME): cv.template,
    vol.Required(ATTR_ANNOTATION): cv.template,
}


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up is called when Home Assistant is loading our component."""

    def handle_annotation(service_call: ServiceCall) -> None:
        """Handle the service call."""
        _LOGGER.debug("Calling annotation")

        filename = service_call.data[ATTR_FILENAME]
        filename.hass = hass
        snapshot_file = filename.render()
        # check if we allow to access to that file
        if not hass.config.is_allowed_path(snapshot_file):
            _LOGGER.error("Can't write %s, no access to path!", snapshot_file)
            return

        annotation = Annotation(service_call, hass)
        if annotation.is_defined:
            annotation.annotate(snapshot_file)

    hass.services.register(
        domain=DOMAIN,
        service=ACTION,
        service_func=handle_annotation,
        schema=vol.Schema(IMAGE_ANNOTATION_ANNOTATE),
    )

    # Return boolean to indicate that initialization was successful.
    return True


class Annotation:
    """Text to be added to snapshot image."""

    annotation_padding: int = 10

    def __init__(self, service_call: ServiceCall, hass: HomeAssistant) -> None:
        """Initialize annotation with ServiceCall and Hass."""
        if ATTR_ANNOTATION in service_call.data:
            self.text = service_call.data[ATTR_ANNOTATION]
            self.hass = hass
            self.is_defined = True
        else:
            self.is_defined = False

    def annotate(self, filename: str) -> bool:
        """Write annotation to the file provided as byte stream direct from camera feed."""
        self.text.hass = self.hass
        annotation_text = self.text.render()
        img = PilImage.open(filename)
        _LOGGER.debug(
            "Annotating snapshot type: %s with text: %s",
            img.format,
            annotation_text,
        )
        drawing = ImageDraw.Draw(img)

        font = ImageFont.load_default()
        text_width, text_height = drawing.textsize(annotation_text, font=font)
        drawing.text(
            (
                (img.width - text_width - self.annotation_padding),
                img.height - text_height - self.annotation_padding,
            ),
            annotation_text,
            fill=(255, 255, 255),
            font=font,
        )

        return img.save(filename)
