import disputeModel from "../models/dispute.model.js";

/*
 * Follows the exact conventions of the audited controllers
 * (booking.controller.js, review.controller.js): req.user.id/role come
 * only from authMiddleware (never trusted from req.body), responses are
 * {success, message?, ...}, errors never leak internals.
 */

export const createDispute = async (req, res) => {
  try {
    const { category, description, booking } = req.body;

    if (!description || !description.trim()) {
      return res.status(400).json({
        success: false,
        message: "Description is required",
      });
    }

    const dispute = await disputeModel.create({
      owner: req.user.id,
      ownerRole: req.user.role,
      category: category || "other",
      description: description.trim(),
      booking: booking || null,
    });

    return res.status(201).json({
      success: true,
      message: "Dispute reported successfully",
      dispute,
    });
  } catch (error) {
    console.log("CREATE DISPUTE ERROR:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

// Owner sees only their own disputes; admin sees all — same ownership
// pattern as getCustomerBookings / getProfessionalBookings.
export const getMyDisputes = async (req, res) => {
  try {
    const filter = req.user.role === "admin" ? {} : { owner: req.user.id };

    const disputes = await disputeModel
      .find(filter)
      .populate("owner", "name email phone")
      .sort({ createdAt: -1 });

    return res.status(200).json({
      success: true,
      disputes,
    });
  } catch (error) {
    console.log("GET MY DISPUTES ERROR:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};

export const getDispute = async (req, res) => {
  try {
    const dispute = await disputeModel
      .findById(req.params.id)
      .populate("owner", "name email phone");

    if (!dispute) {
      return res.status(404).json({
        success: false,
        message: "Dispute not found",
      });
    }

    const isOwner = dispute.owner._id.toString() === req.user.id;
    const isAdmin = req.user.role === "admin";

    if (!isOwner && !isAdmin) {
      // Same response whether it doesn't exist or belongs to someone else.
      return res.status(404).json({
        success: false,
        message: "Dispute not found",
      });
    }

    return res.status(200).json({
      success: true,
      dispute,
    });
  } catch (error) {
    console.log("GET DISPUTE ERROR:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
};
