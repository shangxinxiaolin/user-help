package com.shangui.userhelp.refund.service.impl;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import com.shangui.userhelp.order.domain.Order;
import com.shangui.userhelp.order.service.OrderService;
import com.shangui.userhelp.refund.domain.Refund;
import com.shangui.userhelp.refund.mapper.RefundMapper;
import com.shangui.userhelp.refund.service.RefundService;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class RefundServiceImpl implements RefundService {

    private final OrderService orderService;
    private final RefundMapper refundMapper;

    public RefundServiceImpl(OrderService orderService, RefundMapper refundMapper) {
        this.orderService = orderService;
        this.refundMapper = refundMapper;
    }

    @Override
    public boolean validate(String userId, String orderId) {
        Order order = orderService.query(userId, orderId);
        return isRefundable(order);
    }

    @Override
    public Refund submit(String userId, String orderId, String reason, String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "idempotency_key 不能为空");
        }
        Refund existing = refundMapper.findByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            return existing;
        }
        Order order = orderService.query(userId, orderId);
        if (!isRefundable(order)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "当前订单状态不允许退款");
        }
        Refund refund = new Refund("RF-" + UUID.randomUUID(), orderId, userId, reason, "审核中");
        return refundMapper.save(refund, idempotencyKey);
    }

    private boolean isRefundable(Order order) {
        return !"待付款".equals(order.status()) && !"已签收".equals(order.status());
    }
}
