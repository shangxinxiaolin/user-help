package com.shangui.userhelp.order.mapper;

import com.shangui.userhelp.order.domain.Order;

import java.util.List;

public interface OrderMapper {

    Order findByOrderId(String orderId);

    List<Order> findByUserId(String userId);
}
