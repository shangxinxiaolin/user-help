package com.shangui.userhelp.refund.mapper;

import com.shangui.userhelp.refund.domain.Refund;
import org.springframework.stereotype.Repository;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class MockRefundMapper implements RefundMapper {

    private final Map<String, Refund> refunds = new ConcurrentHashMap<>();

    @Override
    public Refund findByIdempotencyKey(String key) {
        return refunds.get(key);
    }

    @Override
    public Refund save(Refund refund, String idempotencyKey) {
        return refunds.computeIfAbsent(idempotencyKey, ignored -> refund);
    }
}
