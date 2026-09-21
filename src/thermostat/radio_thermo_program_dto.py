from pydantic import RootModel


# Type definition: maps day index (0-6) -> list of integers
class RadioThermoProgramDto(RootModel[dict[str, list[float]]]):

    def get_time_temp_pairs(self, day: str) -> list[tuple[int, float]]:
        """Reads flat array for a day and returns [(minute, temp), ...]"""
        raw = self.root.get(day, [])
        return [(int(raw[i]), raw[i + 1]) for i in range(0, len(raw), 2)]

    def set_time_temp_pairs(self, day: str, pairs: list[tuple[int, float]]) -> None:
        """Sets a day's schedule using tuple pairs [(minute, temp), ...]"""
        flat_list = []
        for minute, temp in pairs:
            flat_list.extend([float(minute), float(temp)])
        self.root[day] = flat_list