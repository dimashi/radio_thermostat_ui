from pydantic import RootModel


# Type definition: maps day index (0-6) -> list of integers
class RadioThermoProgramDto(RootModel[dict[str, list[float]]]):
    pass