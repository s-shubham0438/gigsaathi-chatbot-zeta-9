import mongoose from "mongoose";

/*
 * Mirrors the conventions of the audited models (user.model.js,
 * booking.model.js): timestamps: true, ObjectId refs, a small enum for
 * status. Field names match app/repositories/ticket_repository.py's
 * `disputes` collection documents exactly (see node_backend_patch/README.md).
 */
const disputeSchema = new mongoose.Schema(
  {
    owner: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },

    // Denormalized at creation time so a ticket's role context survives
    // even if the user's role changes later. Matches User.role enum.
    ownerRole: {
      type: String,
      enum: ["customer", "professional", "admin"],
      required: true,
    },

    category: {
      type: String,
      enum: ["payment", "worker_conduct", "customer_conduct", "service_quality", "other"],
      default: "other",
    },

    description: {
      type: String,
      required: true,
      trim: true,
      maxlength: 4000,
    },

    booking: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Booking",
      required: false,
      default: null,
    },

    status: {
      type: String,
      enum: ["open", "in_review", "resolved", "closed"],
      default: "open",
    },
  },
  {
    timestamps: true,
  }
);

disputeSchema.index({ owner: 1, createdAt: -1 });

const disputeModel = mongoose.model("Dispute", disputeSchema);

export default disputeModel;
