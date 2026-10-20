from app.sharing.base import ShareResult, SharingBackend


class NullSharingBackend(SharingBackend):
    pass


def get_backend(cfg):
    if cfg.SHARE_BACKEND == "mac":
        from app.sharing.mac import MacSharingBackend
        return MacSharingBackend()
    if cfg.SHARE_BACKEND == "smtp":
        from app.sharing.smtp import SmtpSharingBackend
        return SmtpSharingBackend()
    return NullSharingBackend()
