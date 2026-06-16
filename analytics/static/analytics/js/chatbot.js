function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(";").shift();
    }
    return "";
}

function appendMessage(text, type) {
    const messages = document.getElementById("chatMessages");
    const bubble = document.createElement("div");
    bubble.className = type === "user" ? "user-message" : "assistant-message";
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chatForm");
    const input = document.getElementById("questionInput");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const question = input.value.trim();
        if (!question) {
            return;
        }

        appendMessage(question, "user");
        input.value = "";
        const loading = appendMessage("Retrieving from generated reports...", "assistant");

        try {
            const response = await fetch("/api/chat/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ question }),
            });
            const payload = await response.json();
            loading.textContent = payload.answer || "No answer was returned.";
        } catch (error) {
            loading.textContent = "The local assistant could not complete the request.";
        }
    });
});
