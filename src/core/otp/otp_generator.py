import logging
from typing import Protocol


from .minotp import totp

logger = logging.getLogger(__name__)


class BaseOTPGenerator(Protocol):

    def get_otp(self, **kwargs) -> str:
        """Get OTP"""

    def representation(self):
        """Implement this to print out the type"""


class TOTPGenerator(BaseOTPGenerator):

    def __init__(self, key: str, time_step=30, digits=6, digest="sha1") -> None:
        self._seed = key
        self.time_step = time_step
        self.digits = digits
        self.digest = digest or "sha1"
        super().__init__()

    def get_otp(self, **kwargs) -> str:
        key = kwargs.get("key", self._seed)
        time_step = kwargs.get("time_step", self.time_step)
        digits = kwargs.get("digits", self.digits)
        digest = kwargs.get("digest", self.digest)
        my_totp = totp(key, time_step, digits, digest)
        return my_totp

    def representation(self):
        logger.info(
            "This is a dummy method: %s, %s, %s",
            self.time_step,
            self.digest,
            self.digits,
        )


class DummyOTPGenerator(BaseOTPGenerator):
    def __init__(self) -> None:
        super().__init__()

    def get_otp(self, **kwargs) -> str:
        logger.info("Dummy OTP does not generate any OTP!")
        return super().get_otp(**kwargs)

    def representation(self):
        logger.info("This is a dummy method")
