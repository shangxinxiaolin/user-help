package com.shangui.userhelp.order.service.impl;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import com.shangui.userhelp.order.domain.Order;
import com.shangui.userhelp.order.mapper.OrderMapper;
import com.shangui.userhelp.order.service.OrderService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class OrderServiceImpl implements OrderService {

    private final OrderMapper orderMapper;

    public OrderServiceImpl(OrderMapper orderMapper) {
        this.orderMapper = orderMapper;
    }

    @Override
    public Order query(String userId, String orderId) {
        validate(userId, orderId);
        Order order = orderMapper.findByOrderId(orderId);
        if (order == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND, "没有找到您的这笔订单");
        }
        if (order.userId() != null && !order.userId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "没有找到您的这笔订单");
        }
        return order.userId() == null
                ? new Order(order.orderId(), userId, order.status(), order.amount(), order.createdAt(),
                order.product(), order.trackingNo())
                : order;
    }

    @Override
    public List<Order> list(String userId) {
        if (userId == null || userId.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "user_id 不能为空");
        }
        return orderMapper.findByUserId(userId);
    }

    private void validate(String userId, String orderId) {
        if (userId == null || userId.isBlank() || orderId == null || orderId.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "user_id 和 order_id 不能为空");
        }
    }
}
