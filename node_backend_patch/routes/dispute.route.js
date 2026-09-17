import express from "express";
import authMiddleware from "../middlewares/authMiddleware.js";
import {
  createDispute,
  getMyDisputes,
  getDispute,
} from "../controllers/dispute.controller.js";

const router = express.Router();

router.use(authMiddleware);

router.post("/", createDispute);
router.get("/", getMyDisputes);
router.get("/:id", getDispute);

export default router;
