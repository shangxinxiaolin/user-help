package com.shangui.userhelp.refund.domain;

public record Refund(String refundId, String orderId, String userId, String reason, String status) {
}
