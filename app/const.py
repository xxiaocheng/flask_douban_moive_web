class Operations:
    CONFIRM = "confirm-email"
    RESET_PASSWORD = "reset-password"
    CHANGE_EMAIL = "change-email"


class MovieType:
    TV = "tv"
    MOVIE = "movie"


class RatingType:
    WISH = 0
    DO = 1
    COLLECT = 2


class MovieCinemaStatus:
    FINISHED = 0
    SHOWING = 1
    COMING = 2


class NotificationType:
    FOLLOW = 0
    RATING_ACTION = 1


class GenderType:
    MALE = 0
    FEMALE = 1


ROLES_PERMISSIONS_MAP = {
    "Locked": [None],
    "User": ["FOLLOW", "COLLECT", "COMMENT"],
    "Moderator": [
        "FOLLOW",
        "COLLECT",
        "COMMENT",
        "UPLOAD",
        "MODERATE",
        "SET_ROLE",
        "HANDLE_REPORT",
        "DELETE_CELEBRITY",
        "DELETE_MOVIE",
        "DELETE_MOVIE",
    ],
    "Administrator": [
        "FOLLOW",
        "COLLECT",
        "COMMENT",
        "UPLOAD",
        "MODERATE",
        "ADMINISTER",
        "LOCK",
        "SET_ROLE",
        "HANDLE_REPORT",
        "DELETE_CELEBRITY",
        "DELETE_MOVIE",
    ],
}
