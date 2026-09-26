package com.shangui.userhelp.refund.mapper;

import com.shangui.userhelp.refund.domain.Refund;

public interface RefundMapper {

    Refund findByIdempotencyKey(String key);

    Refund save(Refund refund, String idempotencyKey);
}
