import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

const baseUrl = (__ENV.BASE_URL || __ENV.API_URL || "").replace(/\/$/, "");

export default function () {
  if (!baseUrl) {
    throw new Error("Set BASE_URL to the CloudFront URL.");
  }

  const response = http.get(`${baseUrl}/api/v1/health`);

  check(response, {
    "health is 200": (res) => res.status === 200,
  });

  sleep(1);
}
