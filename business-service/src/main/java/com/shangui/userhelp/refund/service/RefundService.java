package com.shangui.userhelp.refund.service;

import com.shangui.userhelp.refund.domain.Refund;

public interface RefundService {

    boolean validate(String userId, String orderId);

    Refund submit(String userId, String orderId, String reason, String idempotencyKey);
}
