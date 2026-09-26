package com.shangui.userhelp.order.domain;

public record Order(
        String orderId,
        String userId,
        String status,
        int amount,
        String createdAt,
        String product,
        String trackingNo) {
}
