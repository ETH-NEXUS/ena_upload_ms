from constance import config


class dynamic_settings:
    @classmethod
    def ENA_ENDPOINT(cls):
        return (
            "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA"
            if config.ENA_USE_DEV_ENDPOINT
            else "https://www.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA"
        )

    @classmethod
    def ENA_BROWSER_URL(cls):
        return (
            "https://wwwdev.ebi.ac.uk/ena/browser/view"
            if config.ENA_USE_DEV_ENDPOINT
            else "https://www.ebi.ac.uk/ena/browser/view"
        )
