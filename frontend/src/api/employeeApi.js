// import axios from "axios";

// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// const client = axios.create({ baseURL: API_BASE_URL });

// /** Step 1: create the employee record (no photos yet). */
// export async function createEmployee(payload) {
//   const { data } = await client.post("/api/employees", payload);
//   return data;
// }

// /** Step 2: upload the 3 captured photos; backend returns embeddings stored. */
// export async function enrollFaces(empId, { front, left, right }) {
//   const form = new FormData();
//   form.append("front_image", front, "front.jpg");
//   form.append("left_image", left, "left.jpg");
//   form.append("right_image", right, "right.jpg");

//   const { data } = await client.post(`/api/employees/${empId}/enroll-faces`, form, {
//     headers: { "Content-Type": "multipart/form-data" },
//   });
//   return data;
// }

// export async function listEmployees() {
//   const { data } = await client.get("/api/employees");
//   return data;
// }

// export async function getEmployee(empId) {
//   const { data } = await client.get(`/api/employees/${empId}`);
//   return data;
// }

// export function extractErrorMessage(error) {
//   return error?.response?.data?.detail || error.message || "Something went wrong.";
// }
















import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

/** Step 1: create the employee record (no photos yet). */
export async function createEmployee(payload) {
  const { data } = await client.post("/api/employees", payload);
  return data;
}

/**
 * Check a single captured photo immediately - no DB write.
 * `pose` must be "front" | "left" | "right" - tells the backend which
 * angle to check for, not just whether a face exists.
 */
export async function validatePhoto(blob, pose) {
  const form = new FormData();
  form.append("image", blob, "photo.jpg");
  form.append("pose", pose);
  const { data } = await client.post("/api/employees/validate-photo", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data; // { valid, message }
}

/** Step 2: upload the 3 captured photos; backend returns embeddings stored. */
export async function enrollFaces(empId, { front, left, right }) {
  const form = new FormData();
  form.append("front_image", front, "front.jpg");
  form.append("left_image", left, "left.jpg");
  form.append("right_image", right, "right.jpg");

  const { data } = await client.post(`/api/employees/${empId}/enroll-faces`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listEmployees() {
  const { data } = await client.get("/api/employees");
  return data;
}

export async function getEmployee(empId) {
  const { data } = await client.get(`/api/employees/${empId}`);
  return data;
}

export function extractErrorMessage(error) {
  return error?.response?.data?.detail || error.message || "Something went wrong.";
}