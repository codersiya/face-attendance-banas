"""
Face detection, quality checks, pose (angle) estimation, and embedding generation.

Pose estimation is a lightweight heuristic (not a full 3D head-pose model):
we measure how far the nose sits from the midpoint between the two eyes,
normalized by the distance between the eyes. Facing the camera directly
keeps that offset near zero; turning the head left or right pushes the
nose toward one side, growing the offset in that direction.
This is intentionally simple - accurate enough to tell "front vs turned",
without needing a heavier pose-estimation model.
"""
import io

import face_recognition
import numpy as np
from PIL import Image, ImageOps

from app.config import settings

VALID_POSES = {"front", "left", "right"}


def _load_image(image_bytes: bytes) -> np.ndarray:
    """Decode bytes -> RGB numpy array, auto-correcting EXIF rotation
    (important for phone camera photos)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except Exception as exc:
        raise ValueError(f"Could not read image file: {exc}") from exc
    return np.array(img)


def _avg_point(points: list[tuple[int, int]]) -> tuple[float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _face_yaw_offset(landmarks: dict) -> float:
    """Returns a signed offset roughly proportional to head-turn angle.
    ~0 = facing camera. Positive/negative sign indicates turn direction
    (which side is "left" vs "right" depends on camera mirroring, so the
    frontend is told to just follow the on-screen arrow rather than reason
    about left/right in the abstract)."""
    left_eye = landmarks.get("left_eye")
    right_eye = landmarks.get("right_eye")
    nose_ref = landmarks.get("nose_bridge") or landmarks.get("nose_tip")

    if not left_eye or not right_eye or not nose_ref:
        return 0.0

    left_eye_center = _avg_point(left_eye)
    right_eye_center = _avg_point(right_eye)
    eye_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
    interocular = abs(right_eye_center[0] - left_eye_center[0]) or 1.0

    nose_x = _avg_point(nose_ref)[0]
    return (nose_x - eye_center_x) / interocular


def _classify_pose(offset: float) -> str:
    if abs(offset) <= settings.FACE_FRONT_MAX_OFFSET:
        return "front"
    if offset >= settings.FACE_PROFILE_MIN_OFFSET:
        return "right"
    if offset <= -settings.FACE_PROFILE_MIN_OFFSET:
        return "left"
    return "uncertain"  # turned a bit, but not enough to count as a full profile shot


def analyze_and_validate(image_bytes: bytes, expected_pose: str) -> dict:
    """
    Runs the full pipeline for one photo: face presence/count, size, lighting,
    then pose match against expected_pose ("front" | "left" | "right").

    Returns:
        {
            "valid": bool,
            "message": str,
            "embedding": list[float] | None,   # only set when valid
        }
    """
    if expected_pose not in VALID_POSES:
        raise ValueError(f"Unknown expected_pose '{expected_pose}'")

    image_array = _load_image(image_bytes)
    height, width = image_array.shape[:2]

    face_locations = face_recognition.face_locations(
        image_array, number_of_times_to_upsample=1, model="hog"
    )

    if len(face_locations) == 0:
        return _fail("No face detected. Make sure your face is well lit and fully in frame.")
    if len(face_locations) > 1:
        return _fail("Multiple faces detected. Only the employee should be in frame.")

    top, right, bottom, left = face_locations[0]
    face_area_ratio = ((right - left) * (bottom - top)) / (width * height)

    if face_area_ratio < settings.FACE_MIN_AREA_RATIO:
        return _fail("Face is too small in frame. Move closer to the camera.")
    if face_area_ratio > settings.FACE_MAX_AREA_RATIO:
        return _fail("Face is too close to the camera. Move back a little.")

    brightness = float(np.mean(image_array))
    if brightness < settings.FACE_MIN_BRIGHTNESS:
        return _fail("Image is too dark. Move to a better-lit area.")
    if brightness > settings.FACE_MAX_BRIGHTNESS:
        return _fail("Image is too bright / washed out. Reduce direct light or glare.")

    landmarks_list = face_recognition.face_landmarks(image_array, face_locations=face_locations)
    if not landmarks_list:
        return _fail("Could not read facial features clearly. Please retake the photo.")

    offset = _face_yaw_offset(landmarks_list[0])
    actual_pose = _classify_pose(offset)

    pose_check = _check_pose_match(expected_pose, actual_pose)
    if pose_check is not None:
        return _fail(pose_check)

    encodings = face_recognition.face_encodings(image_array, known_face_locations=face_locations)
    if not encodings:
        return _fail("Could not generate a face embedding. Please retake the photo.")

    return {"valid": True, "message": "Looks good.", "embedding": encodings[0].tolist()}


def _check_pose_match(expected_pose: str, actual_pose: str) -> str | None:
    """Returns an error message if the detected pose doesn't match what was
    asked for, or None if it matches."""
    if expected_pose == "front":
        if actual_pose != "front":
            return "Please face the camera directly - don't turn your head for this shot."
        return None

    # expected_pose is "left" or "right"
    if actual_pose == "front":
        return f"Please turn your head slightly to the {expected_pose} for this shot."
    if actual_pose == "uncertain":
        return "Turn your head a little more - the angle isn't quite enough yet."
    if actual_pose != expected_pose:
        return f"That looks like the wrong direction. Please turn to the {expected_pose} instead."
    return None


def _fail(message: str) -> dict:
    return {"valid": False, "message": message, "embedding": None}


def euclidean_distance(embedding_a: list[float], embedding_b: list[float]) -> float:
    a = np.array(embedding_a)
    b = np.array(embedding_b)
    return float(np.linalg.norm(a - b))