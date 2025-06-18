import { afterAll, afterEach, beforeAll } from "vitest";
import { setupServer } from "msw/node";
import { ws } from "msw";

const chat = ws.link("wss://chat.example.com");

const wsHandlers = [
  chat.addEventListener("connection", ({ client }) => {
    client.addEventListener("message", (event) => {
      console.log("Received message from client:", event.data);
      // Echo the received message back to the client
      client.send(`Server received: ${event.data}`);
    });
  }),
];

const server = setupServer(...wsHandlers);

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

// Close server after all tests
afterAll(() => server.close());

// Reset handlers after each test for test isolation
afterEach(() => server.resetHandlers());
