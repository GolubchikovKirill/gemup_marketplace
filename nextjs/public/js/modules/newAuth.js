import axios from "axios";
import validator from "validator";
import data from "./data.js";

export class AuthManager {
  constructor({ apiUrl }) {
    this.apiUrl = apiUrl;
  }

  validateUserData(data) {
    if (data?.email && !validator.isEmail(data.email)) {
      return "Add correct email";
    }
  }

  async register(userData) {
    const response = await axios.post(`${this.apiUrl}/register`, userData);
    if (response.status == 200) {
      console.log(response.data);
    }
  }
}

export function initAuth() {
  
  (() => {
    const authSubList = ["register", "login"];
    const gemupsData = localStorage.getItem("gemupsData") ? JSON.parse(localStorage.getItem("gemupsData")) : data.gemupsData;
    if (!gemupsData) {
      localStorage.setItem("gemupsData", JSON.stringify(data.gemupsData));
      return;
    }

    const item = gemupsData?.user?.isAuth ? document.querySelector(".noauth") : document.querySelector(".auth");
    if (item) {
      item.style.display = "none";
    }

    const logoutTriggerList = document.querySelectorAll(".logout");
    if (logoutTriggerList.length > 0) {
      logoutTriggerList.forEach((trigger) => {
        trigger.addEventListener("click", () => {
          localStorage.setItem("gemupsData", JSON.stringify({
            ...gemupsData,
            user: {
              ...gemupsData?.user,
              isAuth: false
            }
          }));
          window.location.href = "login.html";
        });
      });
    }

    if (
      gemupsData?.user?.isAuth &&
      authSubList.some((sub) => window.location.href.includes(sub))
    ) {
      window.location.href = "index.html";
    }

    if (
      !gemupsData?.user?.isAuth &&
      !authSubList.some((sub) => window.location.href.includes(sub))
    ) {
      window.location.href = "login.html";
    }
  })();

  document.addEventListener("DOMContentLoaded", () => {
    const authFormList = document.querySelectorAll("#auth");
    const existData = localStorage.getItem("gemupsData") ? JSON.parse(localStorage.getItem("gemupsData")) : data.gemupsData;
    const existUserData = existData.user;

    const authManager = new AuthManager({ apiUrl: "http://127.0.0.1:8080/api/v1/auth" });

    authFormList.forEach((form) => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const userData = Object.fromEntries(formData.entries());

        const errorStr = authManager.validateUserData(userData);
        if (errorStr) {
          alert(errorStr);
          return;
        }

        switch (form.dataset.formType) {
          case "register":
            {
              existUserData.credentials = userData;
              localStorage.setItem("gemupsData", JSON.stringify({ ...existData, user: existUserData }));
              window.location.href = "login.html";
            }
            break;
          case "login":
            {
              if (
                userData?.password === existUserData.credentials.password &&
                userData?.login === existUserData.credentials.username ||
                userData?.login === existUserData.credentials.email
              ) {
                localStorage.setItem("gemupsData", JSON.stringify({ ...existData, user: { ...existUserData, isAuth: true } }));
                window.location.href = "index.html";
              } else {
                alert("Incorrect auth credentials. Please try again");
              }
            }
            break;
          default:
            break;
        }
      });
    });
  });
}
